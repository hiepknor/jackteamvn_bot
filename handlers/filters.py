from aiogram.filters import BaseFilter
from aiogram.types import Message

from config import settings
from utils.logger import logger


class IsAdmin(BaseFilter):
    """Filter for private bot mode access control."""

    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            logger.warning("Unauthorized access attempt without from_user")
            return False

        if not settings.PRIVATE_BOT_MODE:
            return True

        if not settings.admin_id_list:
            await message.answer(
                "🚫 <b>Bot đang ở chế độ riêng tư nhưng chưa cấu hình ADMIN_IDS.</b>\n"
                "Vui lòng liên hệ quản trị viên.",
                parse_mode="HTML",
            )
            return False

        user_id = message.from_user.id
        if user_id in settings.admin_id_list:
            return True

        logger.warning("Unauthorized private-mode access by user_id=%s", user_id)
        await message.answer(
            "🚫 <b>Bạn không có quyền sử dụng bot nội bộ này.</b>\n"
            "Vui lòng liên hệ quản trị viên để được cấp quyền.",
            parse_mode="HTML",
        )
        return False
