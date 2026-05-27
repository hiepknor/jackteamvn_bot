from __future__ import annotations

from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from database.repositories import product_repo
from handlers.filters import IsAllowedUser
from handlers.states import FindProductState
from services.formatter import formatter
from services.thumbnail import thumbnail_service
from utils.logger import logger
from .shared import send_chunked_message


def register(router: Router) -> None:
    @router.message(Command("start"), IsAllowedUser())
    async def cmd_start(message: Message, state: FSMContext):
        await state.clear()
        stats = await product_repo.get_stats()

        await message.answer(
            "🚀 <b>JackTeamVN Bot đã sẵn sàng.</b>\n\n"
            "Công cụ nội bộ để quản lý danh mục sản phẩm và dữ liệu chuẩn hóa.\n\n"
            f"{formatter.format_stats(stats)}\n\n"
            "<b>Lệnh nhanh:</b>\n"
            "📋 /list - Xem danh sách\n"
            "🔎 /find &lt;từ khóa&gt; - Tìm sản phẩm\n"
            "➕ /add - Thêm sản phẩm\n"
            "✏️ /edit - Sửa theo ID\n"
            "🗑️ /delete &lt;id,id2&gt; - Xóa có xác nhận\n"
            "🖼️ /thumbnail &lt;id&gt; - Gán ảnh thumbnail\n"
            "📤 /export - Xuất TXT/CSV\n"
            "📊 /stats - Thống kê\n"
            "❌ /cancel - Hủy thao tác",
            parse_mode="HTML",
        )

    @router.message(Command("help"), IsAllowedUser())
    async def cmd_help(message: Message):
        await message.answer(
            "📖 <b>Hướng dẫn sử dụng bot nội bộ</b>\n\n"
            "<b>Đọc dữ liệu:</b>\n"
            "• /list [limit] [page] - Xem danh sách phân trang\n"
            "• /find &lt;từ khóa&gt; - Tìm theo mã/từ khóa\n"
            "• /stats - Xem thống kê tổng\n\n"
            "<b>Ghi dữ liệu (allowlist):</b>\n"
            "• /add - Thêm nhiều dòng, có preview + xác nhận\n"
            "• /edit - Sửa theo ID, có preview trước/sau\n"
            "• /delete &lt;id,id2,...&gt; - Xóa nhiều ID, có xác nhận\n"
            "• /thumbnail &lt;id&gt; - Gán/thay thumbnail cho sản phẩm\n"
            "• /normalize - Chuẩn hóa dữ liệu hiện có\n"
            "• /backup - Tạo bản sao lưu DB\n"
            "• /export - Xuất dữ liệu TXT/CSV\n\n"
            "<b>Lưu ý:</b>\n"
            "• Nhập <code>yes</code> để xác nhận khi bot yêu cầu\n"
            "• Dùng /cancel để hủy flow đang chạy",
            parse_mode="HTML",
        )

    @router.message(Command("cancel"), StateFilter("*"), IsAllowedUser())
    async def cmd_cancel(message: Message, state: FSMContext):
        await state.clear()
        await message.answer("❌ Đã hủy thao tác hiện tại.", parse_mode="HTML")

    @router.message(Command("list"), IsAllowedUser())
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

        await send_chunked_message(message, text)

    async def _perform_find(message: Message, query: str) -> None:
        rows = await product_repo.search(query, limit=50)
        if not rows:
            await message.answer(
                "😕 <b>Chưa tìm thấy sản phẩm phù hợp.</b>\n\n"
                f"🔎 Từ khóa: <code>{escape(query)}</code>\n"
                "💡 Gợi ý:\n"
                "• Thử từ khóa ngắn hơn (mã ref)\n"
                "• Dùng một phần chuỗi\n"
                "• Xem danh sách với <code>/list 20</code>",
                parse_mode="HTML",
            )
            return

        rows_with_photos = []
        rows_without_photos = []

        for row in rows:
            thumbnail_path = row.get("thumbnail_path")
            resolved_path = thumbnail_service.resolve_path(thumbnail_path)
            if resolved_path and resolved_path.exists():
                rows_with_photos.append((row, resolved_path))
            else:
                rows_without_photos.append(row)

        if rows_without_photos or len(rows) > 1:
            await send_chunked_message(
                message,
                formatter.format_search_summary(query, len(rows), rows_without_photos),
            )

        for row, resolved_path in rows_with_photos:
            thumbnail_path = row.get("thumbnail_path")
            if not resolved_path.exists():
                continue
            try:
                await message.answer_photo(
                    FSInputFile(resolved_path),
                    caption=formatter.format_product_short(row),
                    parse_mode="HTML",
                )
            except Exception as exc:
                logger.warning(
                    "Failed sending thumbnail | product_id=%s path=%s err=%s",
                    row.get("id"),
                    thumbnail_path,
                    exc,
                )

    @router.message(Command("find"), IsAllowedUser())
    async def cmd_find(message: Message, command: CommandObject, state: FSMContext):
        query = (command.args or "").strip()
        if not query:
            await state.set_state(FindProductState.awaiting_query)
            await message.answer(
                "🔎 <b>Nhập từ khóa cần tìm</b>\n"
                "Ví dụ: <code>126528LN</code> hoặc <code>67-02</code>",
                parse_mode="HTML",
            )
            return

        await state.clear()
        await _perform_find(message, query)

    @router.message(FindProductState.awaiting_query, IsAllowedUser())
    async def find_query_handler(message: Message, state: FSMContext):
        query = (message.text or "").strip()
        if not query:
            await message.answer("⚠️ Từ khóa đang trống. Vui lòng nhập lại.")
            return

        await state.clear()
        await _perform_find(message, query)

    @router.message(Command("stats"), IsAllowedUser())
    async def cmd_stats(message: Message):
        stats = await product_repo.get_stats()
        await message.answer(formatter.format_stats(stats), parse_mode="HTML")
