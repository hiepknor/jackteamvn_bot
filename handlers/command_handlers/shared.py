from __future__ import annotations

from typing import Iterable

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from config import settings
from utils.logger import logger

MAX_ADD_LINES = 100
MAX_RAW_LINE_LENGTH = 1000


def actor_tag(message: Message) -> str:
    user = message.from_user
    if not user:
        return "user=unknown"
    username = f"@{user.username}" if user.username else "(no_username)"
    return f"user_id={user.id} username={username}"


async def ensure_admin(message: Message) -> bool:
    """Enforce admin-only action for write operations."""
    user = message.from_user
    if not user:
        await message.answer("🚫 Không xác định được người dùng.")
        return False

    if not settings.admin_id_list:
        await message.answer(
            "🚫 <b>Chưa cấu hình ADMIN_IDS nên tạm khóa lệnh ghi dữ liệu.</b>\n"
            "Vui lòng liên hệ quản trị viên.",
            parse_mode="HTML",
        )
        logger.warning("Write action denied: ADMIN_IDS empty | %s", actor_tag(message))
        return False

    if user.id not in settings.admin_id_list:
        await message.answer("🚫 Bạn không có quyền thực hiện thao tác này.")
        logger.warning("Write action denied for non-admin | %s", actor_tag(message))
        return False

    return True


async def ensure_admin_callback(callback: CallbackQuery) -> bool:
    user = callback.from_user
    if not user:
        if callback.message:
            await callback.message.answer("🚫 Không xác định được người dùng.")
        return False

    if not settings.admin_id_list or user.id not in settings.admin_id_list:
        if callback.message:
            await callback.message.answer("🚫 Bạn không có quyền thực hiện thao tác này.")
        logger.warning("Callback admin denied | user_id=%s", user.id)
        return False

    return True


def format_line_numbers(numbers: Iterable[int], limit: int = 12) -> str:
    values = list(numbers)
    if not values:
        return ""
    head = values[:limit]
    text = ", ".join(str(i) for i in head)
    if len(values) > limit:
        text += f" ... (+{len(values) - limit})"
    return text


async def send_chunked_message(message: Message, text: str, chunk_size: int = 4000) -> None:
    """Send long messages in multiple chunks."""
    if len(text) <= chunk_size:
        await answer_html_with_fallback(message, text)
        return

    lines = text.splitlines(keepends=True)
    chunk = ""

    for line in lines:
        if len(line) > chunk_size:
            if chunk:
                await answer_html_with_fallback(message, chunk)
                chunk = ""
            for i in range(0, len(line), chunk_size):
                await answer_html_with_fallback(message, line[i : i + chunk_size])
            continue

        if len(chunk) + len(line) > chunk_size:
            await answer_html_with_fallback(message, chunk)
            chunk = ""
        chunk += line

    if chunk:
        await answer_html_with_fallback(message, chunk)


async def answer_html_with_fallback(message: Message, text: str) -> None:
    """Prefer HTML, fallback to plain text when entity parsing fails."""
    try:
        await message.answer(text, parse_mode="HTML")
    except TelegramBadRequest as exc:
        if "can't parse entities" not in str(exc).lower():
            raise
        logger.warning("Telegram HTML parse error, fallback plain text: %s", exc)
        await message.answer(text)
