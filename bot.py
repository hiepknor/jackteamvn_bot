import asyncio
import signal
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
from database.connection import db
from database.models import init_database
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


async def main():
    logger.info("=" * 50)
    logger.info("Starting Telegram Bot Professional Edition")
    logger.info("=" * 50)

    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is missing in .env file!")
        raise ValueError("BOT_TOKEN is required")

    if not settings.admin_id_list:
        logger.error("ADMIN_IDS is missing or invalid in .env file!")
        raise ValueError("ADMIN_IDS is required")

    logger.info(f"Admin IDs: {settings.admin_id_list}")
    logger.info(f"Database: {settings.db_path}")
    logger.info(f"Export Dir: {settings.export_dir}")

    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.include_router(commands_router)

    await db.connect()
    await init_database()

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
