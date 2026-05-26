from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import settings
from utils.logger import logger


class IsAllowedUser(BaseFilter):
    """Filter access by TELEGRAM_ALLOWED_USER_IDS when configured."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            logger.warning("Unauthorized access attempt without from_user")
            return False

        user_id = message.from_user.id
        if settings.is_user_allowed(user_id):
            return True

        logger.warning("Unauthorized allowlist access by user_id=%s", user_id)
        await message.answer(
            "🚫 <b>Bạn không có quyền sử dụng bot nội bộ này.</b>\n"
            "Vui lòng liên hệ quản trị viên để được cấp quyền.",
            parse_mode="HTML",
        )
        return False
