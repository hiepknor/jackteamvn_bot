import asyncio
import signal

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import settings
from database.connection import db
from database.models import init_database, restore_latest_backup_if_needed
from handlers.commands import router as commands_router
from utils.fsm_storage import create_fsm_storage
from utils.logger import logger

_is_shutting_down = False


def setup_signal_handlers(loop: asyncio.AbstractEventLoop, dp: Dispatcher, bot: Bot):
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(shutdown(dp, bot)),
            )
        except NotImplementedError:
            logger.warning("Signal handlers are not supported on this platform")
            break


async def shutdown(dp: Dispatcher, bot: Bot):
    global _is_shutting_down
    if _is_shutting_down:
        return
    _is_shutting_down = True

    logger.info("Shutting down bot...")
    await dp.storage.close()
    await bot.session.close()
    await db.close()
    logger.info("Bot stopped gracefully")


async def setup_bot_commands(bot: Bot):
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🚀 Khởi động bot"),
            BotCommand(command="help", description="📖 Hướng dẫn sử dụng"),
            BotCommand(command="list", description="📋 Danh sách sản phẩm"),
            BotCommand(command="find", description="🔎 Tìm sản phẩm"),
            BotCommand(command="add", description="➕ Thêm sản phẩm"),
            BotCommand(command="edit", description="✏️ Sửa sản phẩm"),
            BotCommand(command="delete", description="🗑️ Xóa sản phẩm"),
            BotCommand(command="export", description="📤 Xuất dữ liệu"),
            BotCommand(command="stats", description="📊 Thống kê"),
            BotCommand(command="normalize", description="🧹 Chuẩn hóa dữ liệu"),
            BotCommand(command="backup", description="💾 Sao lưu dữ liệu"),
            BotCommand(command="cancel", description="❌ Hủy thao tác"),
        ]
    )


async def main():
    settings.ensure_directories()

    logger.info("Bot starting")
    logger.info("Startup config | db_path=%s", settings.db_path)
    logger.info("Startup config | private_mode=%s", settings.PRIVATE_BOT_MODE)
    logger.info("Startup config | admin_count=%s", len(settings.admin_id_list))

    storage, fsm_backend = await create_fsm_storage()
    logger.info("Startup config | fsm_backend=%s", fsm_backend)

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    dp.include_router(commands_router)

    restore_status = restore_latest_backup_if_needed()
    if restore_status == "restored":
        logger.info("Startup DB restore completed from latest backup")
    elif restore_status == "new":
        logger.info("Startup DB restore skipped: no valid backup, initialize fresh DB")
    elif restore_status == "failed":
        logger.warning("Startup DB restore failed; bot will continue with current DB path")

    await db.connect()
    await init_database()
    await setup_bot_commands(bot)

    loop = asyncio.get_running_loop()
    setup_signal_handlers(loop, dp, bot)

    logger.info("Bot is running. Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await shutdown(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())
