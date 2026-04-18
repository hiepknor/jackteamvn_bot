from aiogram import Router

from handlers.command_handlers import admin_actions, general, product_flows
from utils.logger import logger

router = Router()

general.register(router)
admin_actions.register(router)
product_flows.register(router)


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
