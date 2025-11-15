import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import ValidationError
from config import bot_token
from web_server import HealthCheckServer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
try:
    if not bot_token:
        raise ValueError("BOT_TOKEN is not set. Please check your .env file")

    bot = Bot(token=bot_token, parse_mode="HTML")
    logger.info("Bot initialized successfully")
except ValidationError:
    logger.error("Invalid bot token provided. Please check your BOT_TOKEN in .env file")
    bot = None
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    bot = None

# Create storage and dispatcher
storage = MemoryStorage()
if bot:
    dp = Dispatcher(bot, storage=storage)

    # Initialize web server for health checks
    web_server = HealthCheckServer(bot, port=int(os.environ.get("PORT", 8080)))

    # Import handlers after dp initialization
    try:
        import handlers
    except ModuleNotFoundError:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        sys.path.insert(0, base_dir)
        pkg_dir = os.path.join(base_dir, "handlers")
        if os.path.isdir(pkg_dir):
            import importlib.util
            try:
                spec = importlib.util.spec_from_file_location(
                    "handlers", os.path.join(pkg_dir, "__init__.py")
                )
                handlers = importlib.util.module_from_spec(spec)
                handlers.__path__ = [pkg_dir]
                sys.modules["handlers"] = handlers
                spec.loader.exec_module(handlers)
            except Exception as e:
                logger.error(f"Failed to load handlers package: {e}")
            for name, rel in [
                ("handlers.start", os.path.join(pkg_dir, "start.py")),
                ("handlers.admin", os.path.join(pkg_dir, "admin", "__init__.py")),
                ("handlers.owner", os.path.join(pkg_dir, "owner", "__init__.py")),
            ]:
                try:
                    s = importlib.util.spec_from_file_location(name, rel)
                    m = importlib.util.module_from_spec(s)
                    sys.modules[name] = m
                    s.loader.exec_module(m)
                except Exception as e:
                    logger.error(f"Failed to import {name}: {e}")
        else:
            logger.error("Handlers directory not found")

    async def on_startup(dp):
        """Actions on bot startup"""
        logger.info("Bot is starting up...")

        # Start web server for health checks
        try:
            await web_server.start_server()
            logger.info("Health check server started successfully")
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")

    async def on_shutdown(dp):
        """Actions on bot shutdown"""
        logger.info("Bot is shutting down...")

        # Close bot session
        await dp.storage.close()
        await dp.storage.wait_closed()

        logger.info("Bot shutdown complete")

    async def main():
        """Main function to start the bot"""
        if not bot:
            logger.error("Bot not initialized. Exiting.")
            return

        try:
            # Start polling
            from aiogram import executor

            logger.info("Starting bot polling...")
            executor.start_polling(
                dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True
            )

        except Exception as e:
            logger.error(f"Error starting bot: {e}")

    if __name__ == "__main__":
        try:
            main()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
else:
    logger.error("Dispatcher not created due to bot initialization failure")
    sys.exit(1)
