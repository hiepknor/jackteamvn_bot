from aiogram.filters import BaseFilter
from aiogram.types import Message
from config import settings
from utils.logger import logger


class IsAdmin(BaseFilter):
    """Filter to check if user is admin for Jack Stock Bot"""
    
    async def __call__(self, message: Message) -> bool:
        if not message.from_user:
            logger.warning("Unauthorized access attempt without from_user")
            return False
        
        if not settings.admin_id_list:
            return True

        user_id = message.from_user.id
        is_admin = user_id in settings.admin_id_list
        
        if not is_admin:
            logger.warning(f"Unauthorized access attempt by user_id={user_id}")
            await message.answer(
                "🚫 <b>Truy cập bị từ chối!</b>\n\n"
                "Bạn không có quyền sử dụng bot này.\n"
                "Vui lòng liên hệ admin để được cấp quyền.",
                parse_mode="HTML"
            )
        
        return is_admin
