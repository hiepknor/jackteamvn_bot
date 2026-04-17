from html import escape

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from handlers.filters import IsAdmin
from handlers.states import AddProductState, EditProductState, DeleteProductState, FindProductState
from database.repositories import product_repo
from database.models import backup_database
from services.formatter import formatter
from services.exporter import exporter
from services.normalizer import normalizer
from utils.logger import logger

router = Router()

MAX_ADD_LINES = 100
MAX_RAW_LINE_LENGTH = 1000


# =========================
# Command Handlers
# =========================

@router.message(Command("start"), IsAdmin())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    stats = await product_repo.get_stats()
    
    await message.answer(
        f"👋 <b>Xin chào Admin!</b>\n\n"
        f"Bot quản lý sản phẩm đã sẵn sàng.\n\n"
        f"{formatter.format_stats(stats)}\n\n"
        f"⚡ <b>Lệnh dùng nhanh:</b>\n"
        f"📋 /list — Xem danh sách sản phẩm\n"
        f"🔍 /find &lt;từ khóa&gt; — Tìm sản phẩm\n"
        f"➕ /add — Thêm sản phẩm mới\n"
        f"✏️ /edit — Sửa sản phẩm theo ID\n"
        f"🗑️ /delete &lt;id[,id2,...]&gt; — Xóa nhanh (có xác nhận)\n"
        f"📤 /export — Xuất file TXT và CSV\n"
        f"📊 /stats — Xem thống kê chi tiết\n"
        f"🧹 /normalize — Chuẩn hóa toàn bộ dữ liệu\n"
        f"💾 /backup — Sao lưu database\n"
        f"❌ /cancel — Hủy thao tác",
        parse_mode="HTML"
    )


@router.message(Command("help"), IsAdmin())
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Danh sách lệnh chi tiết:</b>\n\n"
        "📋 <b>/list</b> — Xem toàn bộ sản phẩm\n"
        "📋 <b>/list 10</b> — Xem 10 sản phẩm/trang\n"
        "📋 <b>/list 10 2</b> — Xem trang 2\n\n"
        "🔍 <b>/find &lt;từ khóa&gt;</b> — Tìm kiếm sản phẩm\n\n"
        "➕ <b>/add</b> — Thêm sản phẩm mới (có xác nhận)\n\n"
        "✏️ <b>/edit</b> — Sửa sản phẩm theo ID\n\n"
        "🗑️ <b>/delete &lt;id[,id2,...]&gt;</b> — Xóa sản phẩm (có xác nhận)\n\n"
        "📤 <b>/export</b> — Xuất file TXT & CSV\n\n"
        "📊 <b>/stats</b> — Xem thống kê hệ thống\n\n"
        "🧹 <b>/normalize</b> — Chuẩn hóa toàn bộ dữ liệu hiện có\n\n"
        "💾 <b>/backup</b> — Sao lưu database\n\n"
        "❌ <b>/cancel</b> — Hủy thao tác hiện tại",
        parse_mode="HTML"
    )


@router.message(Command("cancel"), IsAdmin())
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Đã hủy thao tác.", parse_mode="HTML")


@router.message(Command("list"), IsAdmin())
async def cmd_list(message: Message, command: CommandObject):
    max_limit = 500
    default_limit = 20
    parts = (command.args or "").split()
    if len(parts) > 2:
        await message.answer("⚠️ Dùng: /list [limit] [page]")
        return

    try:
        limit = int(parts[0]) if len(parts) >= 1 else default_limit
        page = int(parts[1]) if len(parts) == 2 else 1
    except ValueError:
        await message.answer("⚠️ Tham số không hợp lệ. Dùng: /list [limit] [page]")
        return

    if limit <= 0 or page <= 0:
        await message.answer("⚠️ Limit và page phải là số nguyên dương.")
        return
    if limit > max_limit:
        await message.answer(f"⚠️ Tối đa {max_limit} sản phẩm mỗi trang.")
        return

    total = await product_repo.count()
    if total == 0:
        await message.answer("📭 Hiện chưa có sản phẩm nào.")
        return

    total_pages = (total + limit - 1) // limit
    if page > total_pages:
        await message.answer(f"⚠️ Trang không hợp lệ. Tổng số trang hiện tại: {total_pages}")
        return

    offset = (page - 1) * limit
    rows = await product_repo.get_all(limit=limit, offset=offset)

    text = formatter.format_product_list(
        rows,
        "📋 Danh sách sản phẩm",
        total=total,
        page=page,
        total_pages=total_pages,
    )

    await _send_chunked_message(message, text)


async def _perform_find(message: Message, query: str) -> None:
    rows = await product_repo.search(query, limit=50)
    if not rows:
        await message.answer(
            "😕 <b>Chưa tìm thấy sản phẩm phù hợp.</b>\n\n"
            f"🔎 Từ khóa: <code>{escape(query)}</code>\n"
            "💡 Bạn có thể thử:\n"
            "• Đổi từ khóa ngắn hơn (ví dụ mã ref)\n"
            "• Dùng một phần từ khóa (ví dụ: <code>67-02</code>)\n"
            "• Xem lại danh sách bằng <code>/list 20</code>",
            parse_mode="HTML",
        )
        return

    text = formatter.format_search_results(query, rows)
    await _send_chunked_message(message, text)


@router.message(Command("find"), IsAdmin())
async def cmd_find(message: Message, command: CommandObject, state: FSMContext):
    query = (command.args or "").strip()
    if not query:
        await state.set_state(FindProductState.awaiting_query)
        await message.answer(
            "🔍 <b>Bạn muốn tìm gì?</b>\n"
            "Hãy gửi từ khóa ở tin nhắn tiếp theo.\n\n"
            "Ví dụ: <code>126528LN</code> hoặc <code>67-02</code>",
            parse_mode="HTML",
        )
        return

    await state.clear()
    await _perform_find(message, query)


@router.message(FindProductState.awaiting_query, IsAdmin())
async def find_query_handler(message: Message, state: FSMContext):
    query = (message.text or "").strip()
    if not query:
        await message.answer("⚠️ Từ khóa đang trống. Vui lòng nhập lại.")
        return

    await state.clear()
    await _perform_find(message, query)


@router.message(Command("export"), IsAdmin())
async def cmd_export(message: Message):
    total = await product_repo.count()
    if total == 0:
        await message.answer("📭 Hiện chưa có sản phẩm nào để xuất file.")
        return
    
    wait_msg = await message.answer(f"⏳ Đang xuất {total} sản phẩm ra file...")
    
    try:
        txt_path = await exporter.export_to_txt()
        csv_path = await exporter.export_to_csv()
        
        await message.answer_document(
            FSInputFile(txt_path), 
            caption=f"📄 File TXT ({total} sản phẩm)"
        )
        await message.answer_document(
            FSInputFile(csv_path), 
            caption=f"📊 File CSV ({total} sản phẩm)"
        )
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        await message.answer(f"❌ Lỗi khi xuất file: {str(e)}")
    finally:
        try:
            await wait_msg.delete()
        except Exception:
            pass


@router.message(Command("stats"), IsAdmin())
async def cmd_stats(message: Message):
    stats = await product_repo.get_stats()
    await message.answer(formatter.format_stats(stats), parse_mode="HTML")


@router.message(Command("normalize"), IsAdmin())
async def cmd_normalize(message: Message):
    total = await product_repo.count()
    if total == 0:
        await message.answer("📭 Hiện chưa có sản phẩm nào để chuẩn hóa.")
        return

    wait_msg = await message.answer(f"⏳ Đang chuẩn hóa {total} sản phẩm...")
    updated = 0
    skipped = 0
    failed = 0
    batch_size = 200
    offset = 0

    try:
        while True:
            rows = await product_repo.get_all(limit=batch_size, offset=offset)
            if not rows:
                break

            for row in rows:
                product_id = row["id"]
                old_text = (row.get("normalized_text") or "").strip()
                old_version = row.get("normalizer_version") or ""
                new_text = normalizer.normalize(old_text)

                if new_text == old_text and old_version == normalizer.VERSION:
                    skipped += 1
                    continue

                success = await product_repo.update(
                    product_id,
                    new_text,
                    message.from_user.id,
                    row,
                    normalizer_version=normalizer.VERSION,
                )
                if success:
                    updated += 1
                else:
                    failed += 1

            offset += batch_size

        await message.answer(
            "✅ <b>Chuẩn hóa hoàn tất</b>\n\n"
            f"🔁 Cập nhật: <b>{updated}</b>\n"
            f"⏭️ Bỏ qua: <b>{skipped}</b>\n"
            f"⚠️ Lỗi: <b>{failed}</b>\n"
            f"🧩 Phiên bản chuẩn hóa: <code>{normalizer.VERSION}</code>",
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error("Normalize command failed: %s", exc, exc_info=exc)
        await message.answer(f"❌ Lỗi khi chuẩn hóa dữ liệu: {escape(str(exc))}", parse_mode="HTML")
    finally:
        try:
            await wait_msg.delete()
        except Exception:
            pass


@router.message(Command("backup"), IsAdmin())
async def cmd_backup(message: Message):
    wait_msg = await message.answer("⏳ Đang sao lưu database...")
    
    try:
        backup_path = await backup_database()
        if backup_path:
            await message.answer(f"✅ Đã sao lưu: <code>{escape(backup_path)}</code>", parse_mode="HTML")
        else:
            await message.answer("⚠️ Sao lưu bị tắt trong cấu hình.")
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        await message.answer(f"❌ Lỗi khi sao lưu: {str(e)}")
    finally:
        try:
            await wait_msg.delete()
        except Exception:
            pass


# =========================
# Add Flow
# =========================

@router.message(Command("add"), IsAdmin())
async def cmd_add(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(AddProductState.raw_lines)
    await message.answer(
        "➕ <b>Thêm sản phẩm mới</b>\n\n"
        "📌 Gửi 1 hoặc nhiều dòng sản phẩm:\n"
        "<code>RL 126528LN leman new 11/2025//1.6m hkd</code>\n"
        "<code>RL 116515LN mete 2022///605.000 hkd</code>\n\n"
        "⚠️ Bot sẽ yêu cầu xác nhận trước khi lưu.",
        parse_mode="HTML"
    )


@router.message(AddProductState.raw_lines, IsAdmin())
async def add_products_handler(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        await message.answer("⚠️ Nội dung trống. Vui lòng gửi lại.")
        return
    
    # Tách dòng và chuẩn hóa từng dòng trước khi preview/lưu.
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        await message.answer("⚠️ Không có dòng hợp lệ để thêm.")
        return
    if len(lines) > MAX_ADD_LINES:
        await message.answer(f"⚠️ Tối đa {MAX_ADD_LINES} dòng mỗi lần thêm.")
        return

    too_long = [idx for idx, line in enumerate(lines, 1) if len(line) > MAX_RAW_LINE_LENGTH]
    if too_long:
        await message.answer(
            "⚠️ Có dòng vượt quá độ dài cho phép "
            f"({MAX_RAW_LINE_LENGTH} ký tự). Dòng lỗi: {', '.join(map(str, too_long[:10]))}"
        )
        return

    normalized_lines = [normalizer.normalize(line) for line in lines]
    empty_after_normalize = [i for i, line in enumerate(normalized_lines, 1) if not line]
    if empty_after_normalize:
        await message.answer(
            "⚠️ Có dòng rỗng sau chuẩn hóa. Dòng lỗi: "
            f"{', '.join(map(str, empty_after_normalize[:10]))}"
        )
        return
    
    # Lưu vào state
    await state.update_data(pending_products=normalized_lines)
    await state.set_state(AddProductState.confirm)
    
    # Hiển thị preview
    preview_lines = [
        "📋 <b>Preview sản phẩm sẽ thêm:</b>",
        ""
    ]
    for i, normalized in enumerate(normalized_lines, 1):
        suffix = "..." if len(normalized) > 80 else ""
        preview_lines.append(f"{i}. <code>{escape(normalized[:80])}</code>{suffix}")
    
    preview_lines.extend([
        "",
        formatter.format_confirmation("thêm", f"{len(lines)} sản phẩm"),
        f"Tổng: {len(lines)} sản phẩm"
    ])
    
    await _send_chunked_message(message, "\n".join(preview_lines))


@router.message(AddProductState.confirm, IsAdmin())
async def add_confirm_handler(message: Message, state: FSMContext):
    if (message.text or "").strip().lower() != "yes":
        await state.clear()
        await message.answer("❌ Đã hủy thêm sản phẩm.")
        return
    
    data = await state.get_data()
    pending_lines = data.get("pending_products", [])
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

    await state.clear()
    await message.answer(f"✅ Đã thêm <b>{count}</b> sản phẩm thành công!", parse_mode="HTML")


# =========================
# Edit Flow
# =========================

@router.message(Command("edit"), IsAdmin())
async def cmd_edit(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(EditProductState.product_id)
    
    rows = await product_repo.get_all(limit=20)
    total = await product_repo.count()
    text = formatter.format_product_list(rows, "📋 Sản phẩm gần nhất (20)", total=total)
    
    await _send_chunked_message(message, text + "\n\n✏️ <b>Nhập ID sản phẩm cần sửa:</b>")


@router.message(EditProductState.product_id, IsAdmin())
async def edit_choose_id(message: Message, state: FSMContext):
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
        parse_mode="HTML"
    )


@router.message(EditProductState.new_raw_line, IsAdmin())
async def edit_new_line(message: Message, state: FSMContext):
    new_line = (message.text or "").strip()
    if not new_line:
        await message.answer("⚠️ Dòng mới không được để trống.")
        return

    normalized_line = normalizer.normalize(new_line)
    if not normalized_line:
        await message.answer("⚠️ Dòng mới rỗng sau chuẩn hóa. Vui lòng nhập lại.")
        return
    
    data = await state.get_data()
    product_id = data["product_id"]

    await state.update_data(new_line=normalized_line)
    await state.set_state(EditProductState.confirm)
    
    await message.answer(
        formatter.format_confirmation(
            "sửa",
            f"ID: {product_id}\nMới: {normalized_line[:100]}..."
        ),
        parse_mode="HTML"
    )


@router.message(EditProductState.confirm, IsAdmin())
async def edit_confirm_handler(message: Message, state: FSMContext):
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
        updated = await product_repo.get_by_id(product_id)
        await message.answer(
            f"✅ Đã cập nhật sản phẩm:\n\n{formatter.format_product_short(updated)}",
            parse_mode="HTML"
        )
    else:
        await message.answer("❌ Cập nhật thất bại. Sản phẩm có thể không còn tồn tại.")


# =========================
# Delete Flow
# =========================


async def _handle_delete_ids_input(message: Message, state: FSMContext, text: str) -> None:
    text = (text or "").strip()
    if not text:
        await message.answer("⚠️ Vui lòng nhập ID cần xóa.")
        return

    # Parse IDs
    import re
    raw_parts = re.split(r"[,\s]+", text.strip())
    ids = []
    invalid_parts = []

    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        if part.isdigit() and int(part) > 0:
            ids.append(int(part))
        else:
            invalid_parts.append(part)

    ids = list(dict.fromkeys(ids))  # Remove duplicates

    if not ids:
        await message.answer("⚠️ Không có ID hợp lệ. Ví dụ: <code>1,2,3,5</code>")
        return

    # Show preview
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
        products_to_delete=products_to_delete
    )
    await state.set_state(DeleteProductState.confirm)

    preview_lines = [
        "🗑️ <b>Xác nhận xóa:</b>",
        ""
    ]
    for product in products_to_delete:
        display_text = product.get("normalized_text") or ""
        preview_lines.append(
            f"• <code>#{product['id']}</code> <code>{escape(display_text[:60])}</code>"
            f"{'...' if len(display_text) > 60 else ''}"
        )

    if invalid_parts:
        preview_lines.extend([
            "",
            f"⚠️ ID không hợp lệ đã bỏ qua: {', '.join(invalid_parts)}"
        ])

    if not_found_ids:
        preview_lines.extend([
            "",
            f"⚠️ Không tìm thấy: {', '.join(map(str, not_found_ids))}"
        ])

    preview_lines.extend([
        "",
        formatter.format_confirmation("xóa", f"{len(products_to_delete)} sản phẩm")
    ])

    await _send_chunked_message(message, "\n".join(preview_lines))


@router.message(Command("delete"), IsAdmin())
async def cmd_delete(message: Message, state: FSMContext, command: CommandObject):
    await state.clear()
    args = (command.args or "").strip()
    if args:
        await _handle_delete_ids_input(message, state, args)
        return

    await state.set_state(DeleteProductState.product_ids)

    rows = await product_repo.get_all(limit=20)
    total = await product_repo.count()
    text = formatter.format_product_list(rows, "📋 Sản phẩm gần nhất (20)", total=total)

    await _send_chunked_message(
        message,
        text + "\n\n🗑️ <b>Nhập 1 hoặc nhiều ID cần xóa:</b>\nVí dụ: <code>1,2,3,5</code>"
    )


@router.message(DeleteProductState.product_ids, IsAdmin())
async def delete_choose_ids(message: Message, state: FSMContext):
    await _handle_delete_ids_input(message, state, message.text or "")


@router.message(DeleteProductState.confirm, IsAdmin())
async def delete_confirm_handler(message: Message, state: FSMContext):
    if (message.text or "").strip().lower() != "yes":
        await state.clear()
        await message.answer("❌ Đã hủy xóa sản phẩm.")
        return
    
    data = await state.get_data()
    ids = data["delete_ids"]
    
    deleted_ids, not_found_ids = await product_repo.delete_batch(ids, message.from_user.id)
    await state.clear()
    
    lines = []
    if deleted_ids:
        lines.append(f"✅ Đã xóa <b>{len(deleted_ids)}</b> sản phẩm:")
        for pid in deleted_ids[:10]:
            lines.append(f"  • #{pid}")
        if len(deleted_ids) > 10:
            lines.append(f"  ... và {len(deleted_ids) - 10} sản phẩm khác")
    
    if not_found_ids:
        lines.append("")
        lines.append(f"❓ Không tìm thấy: {', '.join(map(str, not_found_ids))}")
    
    await message.answer("\n".join(lines), parse_mode="HTML")


# =========================
# Helper Functions
# =========================

async def _send_chunked_message(message: Message, text: str, chunk_size: int = 4000) -> None:
    """Gửi tin nhắn dài thành nhiều chunk"""
    if len(text) <= chunk_size:
        await _answer_html_with_fallback(message, text)
        return
    
    lines = text.splitlines(keepends=True)
    chunk = ""
    
    for line in lines:
        if len(line) > chunk_size:
            if chunk:
                await _answer_html_with_fallback(message, chunk)
                chunk = ""
            for i in range(0, len(line), chunk_size):
                await _answer_html_with_fallback(message, line[i:i + chunk_size])
            continue

        if len(chunk) + len(line) > chunk_size:
            await _answer_html_with_fallback(message, chunk)
            chunk = ""
        chunk += line
    
    if chunk:
        await _answer_html_with_fallback(message, chunk)


async def _answer_html_with_fallback(message: Message, text: str) -> None:
    """Ưu tiên gửi HTML, fallback sang text thường nếu parse lỗi."""
    try:
        await message.answer(text, parse_mode="HTML")
    except TelegramBadRequest as exc:
        if "can't parse entities" not in str(exc).lower():
            raise
        logger.warning("Telegram HTML parse lỗi, fallback plain text: %s", exc)
        await message.answer(text)


# =========================
# Error Handler
# =========================

@router.errors()
async def error_handler(event):
    exception = getattr(event, "exception", None)
    logger.error("Error in handler: %s", exception, exc_info=exception)
    update = getattr(event, "update", None)
    message = getattr(update, "message", None)
    if message:
        try:
            await message.answer("❌ Có lỗi xảy ra khi xử lý lệnh. Vui lòng thử lại hoặc dùng /cancel.")
        except Exception:
            pass
    return True
