import asyncio
import signal
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from config import settings
from database.connection import db
from database.models import init_database, restore_latest_backup_if_needed
from handlers.commands import router as commands_router
from utils.logger import logger

_is_shutting_down = False

def setup_signal_handlers(loop: asyncio.AbstractEventLoop, dp: Dispatcher, bot: Bot):
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(shutdown(dp, bot))
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
    """Register command menu with icons in Telegram UI."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🚀 Khởi động bot"),
            BotCommand(command="help", description="📖 Hướng dẫn sử dụng"),
            BotCommand(command="add", description="➕ Thêm và chuẩn hóa sản phẩm"),
            BotCommand(command="list", description="📋 Danh sách sản phẩm"),
            BotCommand(command="find", description="🔍 Tìm sản phẩm"),
            BotCommand(command="edit", description="✏️ Sửa theo ID"),
            BotCommand(command="delete", description="🗑️ Xóa theo ID / 1,2,3"),
            BotCommand(command="export", description="📤 Xuất TXT/CSV"),
            BotCommand(command="stats", description="📊 Thống kê"),
            BotCommand(command="normalize", description="🧹 Chuẩn hóa toàn bộ DB"),
            BotCommand(command="backup", description="💾 Sao lưu DB"),
            BotCommand(command="cancel", description="❌ Hủy thao tác"),
        ]
    )


async def main():
    logger.info("=" * 50)
    logger.info("Starting Telegram Bot Professional Edition")
    logger.info("=" * 50)

    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in .env file!")
        raise ValueError("BOT_TOKEN is required")

    invalid_admin_ids = settings.invalid_admin_id_tokens
    if invalid_admin_ids:
        logger.error("Invalid ADMIN_IDS tokens: %s", invalid_admin_ids)
        raise ValueError("ADMIN_IDS contains invalid values. Use comma-separated numeric Telegram IDs.")

    if settings.admin_id_list:
        logger.info(f"Admin-only mode enabled. Admin IDs: {settings.admin_id_list}")
    else:
        logger.info("Open mode enabled. ADMIN_IDS is empty, all users are allowed.")
    logger.info(f"Database: {settings.db_path}")
    logger.info(f"Export Dir: {settings.export_dir}")

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(commands_router)

    restore_status = restore_latest_backup_if_needed()
    if restore_status == "restored":
        logger.info("Startup DB restore completed from latest backup.")
    elif restore_status == "new":
        logger.info("Startup DB restore skipped: no valid backup, initialize fresh DB.")
    elif restore_status == "failed":
        logger.warning("Startup DB restore failed; bot will continue with current DB path.")

    await db.connect()
    await init_database()
    await setup_bot_commands(bot)

    loop = asyncio.get_running_loop()
    setup_signal_handlers(loop, dp, bot)

    logger.info("Bot is running... Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await shutdown(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())
