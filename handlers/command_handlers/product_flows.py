from __future__ import annotations

import re
from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.repositories import product_repo
from handlers.filters import IsAdmin
from handlers.states import AddProductState, DeleteProductState, EditProductState
from services.formatter import formatter
from services.normalizer import normalizer
from utils.logger import logger
from .shared import (
    MAX_ADD_LINES,
    MAX_RAW_LINE_LENGTH,
    actor_tag,
    ensure_admin,
    format_line_numbers,
    send_chunked_message,
)


def register(router: Router) -> None:
    @router.message(Command("add"), IsAdmin())
    async def cmd_add(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            return

        await state.clear()
        await state.set_state(AddProductState.raw_lines)
        await message.answer(
            "➕ <b>Thêm sản phẩm mới</b>\n\n"
            "📌 Gửi 1 hoặc nhiều dòng, mỗi dòng là 1 sản phẩm:\n"
            "<code>RL 126528LN leman new 11/2025//1.6m hkd</code>\n"
            "<code>RL 116515LN mete 2022///605.000 hkd</code>\n\n"
            "Bot sẽ preview trước khi lưu. Dùng /cancel để hủy.",
            parse_mode="HTML",
        )

    @router.message(AddProductState.raw_lines, IsAdmin())
    async def add_products_handler(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            await state.clear()
            return

        text = (message.text or "").strip()
        if not text:
            await message.answer("⚠️ Nội dung trống. Vui lòng gửi lại.")
            return

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            await message.answer("⚠️ Không có dòng hợp lệ để thêm.")
            return
        if len(lines) > MAX_ADD_LINES:
            await message.answer(f"⚠️ Tối đa {MAX_ADD_LINES} dòng mỗi lần thêm.")
            return

        valid_lines: list[str] = []
        too_long_idx: list[int] = []
        empty_after_normalize_idx: list[int] = []

        for idx, line in enumerate(lines, 1):
            if len(line) > MAX_RAW_LINE_LENGTH:
                too_long_idx.append(idx)
                continue
            normalized = normalizer.normalize(line)
            if not normalized:
                empty_after_normalize_idx.append(idx)
                continue
            valid_lines.append(normalized)

        invalid_count = len(too_long_idx) + len(empty_after_normalize_idx)
        if not valid_lines:
            await message.answer(
                "⚠️ Không có dòng hợp lệ để thêm.\n"
                f"• Tổng dòng nhận: {len(lines)}\n"
                f"• Dòng quá dài: {len(too_long_idx)}\n"
                f"• Dòng rỗng sau chuẩn hóa: {len(empty_after_normalize_idx)}",
                parse_mode="HTML",
            )
            return

        await state.update_data(
            pending_products=valid_lines,
            add_total_input=len(lines),
            add_invalid_count=invalid_count,
        )
        await state.set_state(AddProductState.confirm)

        preview_lines = ["📋 <b>Preview sản phẩm sẽ thêm</b>", ""]
        for i, normalized in enumerate(valid_lines[:30], 1):
            suffix = "..." if len(normalized) > 80 else ""
            preview_lines.append(f"{i}. <code>{escape(normalized[:80])}</code>{suffix}")
        if len(valid_lines) > 30:
            preview_lines.append(f"... và {len(valid_lines) - 30} dòng hợp lệ khác")

        preview_lines.extend(
            [
                "",
                f"✅ Hợp lệ: <b>{len(valid_lines)}</b>",
                f"⚠️ Không hợp lệ: <b>{invalid_count}</b>",
            ]
        )

        if too_long_idx:
            preview_lines.append(
                f"• Dòng quá dài (&gt;{MAX_RAW_LINE_LENGTH} ký tự): {format_line_numbers(too_long_idx)}"
            )
        if empty_after_normalize_idx:
            preview_lines.append(
                f"• Dòng rỗng sau chuẩn hóa: {format_line_numbers(empty_after_normalize_idx)}"
            )

        preview_lines.extend(["", formatter.format_confirmation("thêm", f"{len(valid_lines)} sản phẩm")])
        await send_chunked_message(message, "\n".join(preview_lines))

    @router.message(AddProductState.confirm, IsAdmin())
    async def add_confirm_handler(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            await state.clear()
            return

        if (message.text or "").strip().lower() != "yes":
            await state.clear()
            await message.answer("❌ Đã hủy thêm sản phẩm.")
            return

        data = await state.get_data()
        pending_lines = data.get("pending_products", [])
        invalid_count = int(data.get("add_invalid_count", 0))

        try:
            count = await product_repo.create_batch(
                pending_lines,
                message.from_user.id,
                normalizer_version=normalizer.VERSION,
            )
        except Exception as exc:
            logger.error("Add products failed: %s", exc, exc_info=exc)
            await state.clear()
            await message.answer("❌ Lỗi khi thêm sản phẩm. Không có dữ liệu nào được lưu.")
            return

        logger.info(
            "Admin add success | %s | created=%s invalid=%s",
            actor_tag(message),
            count,
            invalid_count,
        )
        await state.clear()
        await message.answer(
            "✅ Đã thêm sản phẩm thành công.\n"
            f"• Đã lưu: <b>{count}</b>\n"
            f"• Bỏ qua: <b>{invalid_count}</b>",
            parse_mode="HTML",
        )

    @router.message(Command("edit"), IsAdmin())
    async def cmd_edit(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            return

        await state.clear()
        await state.set_state(EditProductState.product_id)

        rows = await product_repo.get_all(limit=20)
        total = await product_repo.count()
        text = formatter.format_product_list(rows, "📋 Sản phẩm gần nhất (20)", total=total)

        await send_chunked_message(message, text + "\n\n✏️ <b>Nhập ID sản phẩm cần sửa:</b>")

    @router.message(EditProductState.product_id, IsAdmin())
    async def edit_choose_id(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            await state.clear()
            return

        text = (message.text or "").strip()
        if not text.isdigit() or int(text) <= 0:
            await message.answer("⚠️ ID không hợp lệ. Vui lòng nhập số nguyên dương.")
            return

        product_id = int(text)
        product = await product_repo.get_by_id(product_id)

        if not product:
            await message.answer("❓ Không tìm thấy sản phẩm. Nhập lại ID hoặc /cancel để hủy.")
            return

        await state.update_data(product_id=product_id, old_data=product)
        await state.set_state(EditProductState.new_raw_line)

        await message.answer(
            "📋 <b>Sản phẩm hiện tại:</b>\n\n"
            f"{formatter.format_product_detail(product)}\n\n"
            "✏️ <b>Gửi dòng mới để thay thế:</b>",
            parse_mode="HTML",
        )

    @router.message(EditProductState.new_raw_line, IsAdmin())
    async def edit_new_line(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            await state.clear()
            return

        new_line = (message.text or "").strip()
        if not new_line:
            await message.answer("⚠️ Dòng mới không được để trống.")
            return

        if len(new_line) > MAX_RAW_LINE_LENGTH:
            await message.answer(f"⚠️ Dòng mới vượt quá {MAX_RAW_LINE_LENGTH} ký tự.")
            return

        normalized_line = normalizer.normalize(new_line)
        if not normalized_line:
            await message.answer("⚠️ Dòng mới rỗng sau chuẩn hóa. Vui lòng nhập lại.")
            return

        data = await state.get_data()
        product_id = data["product_id"]
        old_data = data["old_data"]
        old_text = old_data.get("normalized_text") or ""

        await state.update_data(new_line=normalized_line)
        await state.set_state(EditProductState.confirm)

        await message.answer(
            "📋 <b>Preview chỉnh sửa</b>\n"
            f"🆔 ID: <code>{product_id}</code>\n"
            f"🔸 Cũ: <code>{escape(old_text[:120])}</code>{'...' if len(old_text) > 120 else ''}\n"
            f"🔹 Mới: <code>{escape(normalized_line[:120])}</code>{'...' if len(normalized_line) > 120 else ''}\n\n"
            "Gõ <code>yes</code> để xác nhận, hoặc nhập nội dung khác để hủy.",
            parse_mode="HTML",
        )

    @router.message(EditProductState.confirm, IsAdmin())
    async def edit_confirm_handler(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            await state.clear()
            return

        if (message.text or "").strip().lower() != "yes":
            await state.clear()
            await message.answer("❌ Đã hủy sửa sản phẩm.")
            return

        data = await state.get_data()
        product_id = data["product_id"]
        new_line = data["new_line"]
        old_data = data["old_data"]

        success = await product_repo.update(
            product_id,
            new_line,
            message.from_user.id,
            old_data,
            normalizer_version=normalizer.VERSION,
        )
        await state.clear()

        if success:
            logger.info("Admin edit success | %s | product_id=%s", actor_tag(message), product_id)
            updated = await product_repo.get_by_id(product_id)
            await message.answer(
                f"✅ Đã cập nhật sản phẩm:\n\n{formatter.format_product_short(updated)}",
                parse_mode="HTML",
            )
        else:
            await message.answer("❌ Cập nhật thất bại. Sản phẩm có thể không còn tồn tại.")

    async def _handle_delete_ids_input(message: Message, state: FSMContext, text: str) -> None:
        text = (text or "").strip()
        if not text:
            await message.answer("⚠️ Vui lòng nhập ID cần xóa.")
            return

        raw_parts = re.split(r"[,\s]+", text.strip())
        ids: list[int] = []
        invalid_parts: list[str] = []

        for part in raw_parts:
            part = part.strip()
            if not part:
                continue
            if part.isdigit() and int(part) > 0:
                ids.append(int(part))
            else:
                invalid_parts.append(part)

        ids = list(dict.fromkeys(ids))

        if not ids:
            await message.answer("⚠️ Không có ID hợp lệ. Ví dụ: <code>1,2,3</code>", parse_mode="HTML")
            return

        products_to_delete = []
        not_found_ids = []

        for product_id in ids:
            product = await product_repo.get_by_id(product_id)
            if product:
                products_to_delete.append(product)
            else:
                not_found_ids.append(product_id)

        if not products_to_delete:
            lines = ["⚠️ Không có sản phẩm hợp lệ để xóa."]
            if invalid_parts:
                lines.append(f"ID không hợp lệ đã bỏ qua: {', '.join(invalid_parts)}")
            if not_found_ids:
                lines.append(f"Không tìm thấy: {', '.join(map(str, not_found_ids))}")

            current_state = await state.get_state()
            if current_state == DeleteProductState.product_ids.state:
                lines.append("Vui lòng nhập lại ID hoặc /cancel để hủy.")
            else:
                await state.clear()
                lines.append("Thử lại với cú pháp: /delete 1,2,3")

            await message.answer("\n".join(lines), parse_mode="HTML")
            return

        await state.update_data(
            delete_ids=ids,
            not_found_ids=not_found_ids,
            products_to_delete=products_to_delete,
        )
        await state.set_state(DeleteProductState.confirm)

        preview_lines = ["🗑️ <b>Xác nhận xóa:</b>", ""]
        for product in products_to_delete:
            display_text = product.get("normalized_text") or ""
            preview_lines.append(
                f"• <code>#{product['id']}</code> <code>{escape(display_text[:60])}</code>"
                f"{'...' if len(display_text) > 60 else ''}"
            )

        preview_lines.extend(
            [
                "",
                f"✅ Tìm thấy: <b>{len(products_to_delete)}</b>",
                f"⚠️ Không tìm thấy: <b>{len(not_found_ids)}</b>",
                f"⚠️ ID sai định dạng: <b>{len(invalid_parts)}</b>",
            ]
        )

        if invalid_parts:
            preview_lines.append(f"ID không hợp lệ: {', '.join(invalid_parts)}")
        if not_found_ids:
            preview_lines.append(f"ID không tồn tại: {', '.join(map(str, not_found_ids))}")

        preview_lines.extend(["", formatter.format_confirmation("xóa", f"{len(products_to_delete)} sản phẩm")])

        await send_chunked_message(message, "\n".join(preview_lines))

    @router.message(Command("delete"), IsAdmin())
    async def cmd_delete(message: Message, state: FSMContext, command: CommandObject):
        if not await ensure_admin(message):
            return

        await state.clear()
        args = (command.args or "").strip()
        if args:
            await _handle_delete_ids_input(message, state, args)
            return

        await state.set_state(DeleteProductState.product_ids)

        rows = await product_repo.get_all(limit=20)
        total = await product_repo.count()
        text = formatter.format_product_list(rows, "📋 Sản phẩm gần nhất (20)", total=total)

        await send_chunked_message(
            message,
            text + "\n\n🗑️ <b>Nhập 1 hoặc nhiều ID cần xóa:</b>\nVí dụ: <code>1,2,3,5</code>",
        )

    @router.message(DeleteProductState.product_ids, IsAdmin())
    async def delete_choose_ids(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            await state.clear()
            return
        await _handle_delete_ids_input(message, state, message.text or "")

    @router.message(DeleteProductState.confirm, IsAdmin())
    async def delete_confirm_handler(message: Message, state: FSMContext):
        if not await ensure_admin(message):
            await state.clear()
            return

        if (message.text or "").strip().lower() != "yes":
            await state.clear()
            await message.answer("❌ Đã hủy xóa sản phẩm.")
            return

        data = await state.get_data()
        ids = data["delete_ids"]

        deleted_ids, not_found_ids = await product_repo.delete_batch(ids, message.from_user.id)
        await state.clear()

        logger.info(
            "Admin delete completed | %s | requested=%s deleted=%s not_found=%s",
            actor_tag(message),
            len(ids),
            len(deleted_ids),
            len(not_found_ids),
        )

        lines = []
        if deleted_ids:
            lines.append(f"✅ Đã xóa <b>{len(deleted_ids)}</b> sản phẩm:")
            for pid in deleted_ids[:10]:
                lines.append(f"• #{pid}")
            if len(deleted_ids) > 10:
                lines.append(f"... và {len(deleted_ids) - 10} sản phẩm khác")

        if not_found_ids:
            lines.append("")
            lines.append(f"❓ Không tìm thấy: {', '.join(map(str, not_found_ids))}")

        await message.answer("\n".join(lines), parse_mode="HTML")
