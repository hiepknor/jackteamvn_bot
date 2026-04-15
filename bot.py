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


def setup_signal_handlers(dp: Dispatcher, bot: Bot):
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown(dp, bot))
        )


async def shutdown(dp: Dispatcher, bot: Bot):
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

    setup_signal_handlers(dp, bot)

    logger.info("Bot is running... Press Ctrl+C to stop.")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await shutdown(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())