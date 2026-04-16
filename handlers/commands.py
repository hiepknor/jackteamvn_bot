from html import escape

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, FSInputFile

from handlers.filters import IsAdmin
from handlers.states import AddProductState, EditProductState, DeleteProductState
from database.repositories import product_repo
from database.models import backup_database
from services.parser import product_parser
from services.formatter import formatter
from services.exporter import exporter
from utils.logger import logger

router = Router()


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
        f"🗑️ /delete — Xóa sản phẩm theo ID\n"
        f"📤 /export — Xuất file TXT và CSV\n"
        f"📊 /stats — Xem thống kê chi tiết\n"
        f"💾 /backup — Sao lưu database\n"
        f"❌ /cancel — Hủy thao tác",
        parse_mode="HTML"
    )


@router.message(Command("help"), IsAdmin())
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Danh sách lệnh chi tiết:</b>\n\n"
        "📋 <b>/list</b> — Xem toàn bộ sản phẩm\n"
        "📋 <b>/list 10</b> — Xem 10 sản phẩm gần nhất\n\n"
        "🔍 <b>/find &lt;từ khóa&gt;</b> — Tìm kiếm sản phẩm\n\n"
        "➕ <b>/add</b> — Thêm sản phẩm mới (có xác nhận)\n\n"
        "✏️ <b>/edit</b> — Sửa sản phẩm theo ID\n\n"
        "🗑️ <b>/delete</b> — Xóa sản phẩm theo ID(s)\n\n"
        "📤 <b>/export</b> — Xuất file TXT & CSV\n\n"
        "📊 <b>/stats</b> — Xem thống kê hệ thống\n\n"
        "💾 <b>/backup</b> — Sao lưu database\n\n"
        "❌ <b>/cancel</b> — Hủy thao tác hiện tại",
        parse_mode="HTML"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Đã hủy thao tác.", parse_mode="HTML")


@router.message(Command("list"), IsAdmin())
async def cmd_list(message: Message, command: CommandObject):
    try:
        limit = int(command.args) if command.args else None
    except ValueError:
        await message.answer("⚠️ Số lượng không hợp lệ. Dùng: /list [số]")
        return

    if limit is not None and limit <= 0:
        await message.answer("⚠️ Số lượng phải là số nguyên dương. Dùng: /list [số]")
        return
    
    total = await product_repo.count()
    rows = await product_repo.get_all(limit=limit or 50)
    
    text = formatter.format_product_list(
        rows, 
        "📋 Danh sách sản phẩm",
        total=total
    )
    
    await _send_chunked_message(message, text)


@router.message(Command("find"), IsAdmin())
async def cmd_find(message: Message, command: CommandObject):
    query = (command.args or "").strip()
    if not query:
        await message.answer(
            "⚠️ Dùng: <code>/find &lt;từ khóa&gt;</code>\n"
            "Ví dụ: <code>/find 126528LN</code>",
            parse_mode="HTML"
        )
        return
    
    rows = await product_repo.search(query, limit=50)
    if not rows:
        await message.answer(
            f"😕 Không tìm thấy sản phẩm nào với từ khóa: <b>{query}</b>",
            parse_mode="HTML"
        )
        return
    
    text = formatter.format_search_results(query, rows)
    await _send_chunked_message(message, text)


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
        
        await wait_msg.delete()
    except Exception as e:
        logger.error(f"Export failed: {e}")
        await message.answer(f"❌ Lỗi khi xuất file: {str(e)}")


@router.message(Command("stats"), IsAdmin())
async def cmd_stats(message: Message):
    stats = await product_repo.get_stats()
    await message.answer(formatter.format_stats(stats), parse_mode="HTML")


@router.message(Command("backup"), IsAdmin())
async def cmd_backup(message: Message):
    wait_msg = await message.answer("⏳ Đang sao lưu database...")
    
    try:
        backup_path = await backup_database()
        if backup_path:
            await message.answer(f"✅ Đã sao lưu: <code>{backup_path}</code>", parse_mode="HTML")
        else:
            await message.answer("⚠️ Sao lưu bị tắt trong cấu hình.")
        
        await wait_msg.delete()
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        await message.answer(f"❌ Lỗi khi sao lưu: {str(e)}")


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
    
    # Parse và lưu tạm
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    parsed_products = []
    warnings = []
    
    for line in lines:
        parsed = product_parser.parse(line)
        parsed_products.append((line, parsed))
        _, line_warnings = product_parser.validate_parsed_data(parsed)
        warnings.extend([f"#{len(parsed_products)}: {w}" for w in line_warnings])
    
    # Lưu vào state
    await state.update_data(
        pending_products=parsed_products,
        warnings=warnings
    )
    await state.set_state(AddProductState.confirm)
    
    # Hiển thị preview
    preview_lines = [
        "📋 <b>Preview sản phẩm sẽ thêm:</b>",
        ""
    ]
    for i, (raw, parsed) in enumerate(parsed_products, 1):
        preview_lines.append(f"{i}. <code>{escape(raw[:80])}</code>...")
        brand = escape(str(parsed.get("brand") or ""))
        model = escape(str(parsed.get("model") or ""))
        price_text = escape(str(parsed.get("price_text") or ""))
        currency = escape(str(parsed.get("currency") or ""))
        preview_lines.append(
            f"   Brand: {brand}, Model: {model}, Price: {price_text} {currency}"
        )
    
    if warnings:
        safe_warnings = [escape(w) for w in warnings]
        preview_lines.extend(["", "⚠️ <b>Cảnh báo:</b>"] + safe_warnings)
    
    preview_lines.extend([
        "",
        formatter.format_confirmation("thêm", f"{len(parsed_products)} sản phẩm"),
        f"Tổng: {len(parsed_products)} sản phẩm"
    ])
    
    await _send_chunked_message(message, "\n".join(preview_lines))


@router.message(AddProductState.confirm, IsAdmin())
async def add_confirm_handler(message: Message, state: FSMContext):
    if (message.text or "").strip().lower() != "yes":
        await state.clear()
        await message.answer("❌ Đã hủy thêm sản phẩm.")
        return
    
    data = await state.get_data()
    parsed_products = data.get("pending_products", [])
    
    count = 0
    for raw, parsed in parsed_products:
        product_id = await product_repo.create(raw, parsed, message.from_user.id)
        if product_id:
            count += 1
    
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
    
    data = await state.get_data()
    product_id = data["product_id"]
    
    parsed = product_parser.parse(new_line)
    
    await state.update_data(new_line=new_line, parsed_data=parsed)
    await state.set_state(EditProductState.confirm)
    
    await message.answer(
        formatter.format_confirmation(
            "sửa",
            f"ID: {product_id}\nMới: {new_line[:100]}..."
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
    parsed_data = data["parsed_data"]
    old_data = data["old_data"]
    
    success = await product_repo.update(product_id, new_line, parsed_data, 
                                        message.from_user.id, old_data)
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

@router.message(Command("delete"), IsAdmin())
async def cmd_delete(message: Message, state: FSMContext):
    await state.clear()
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
    text = (message.text or "").strip()
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
        preview_lines.append(f"• #{product['id']} {product['raw_text'][:60]}...")

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
    return True
