import asyncio
import logging
import os
from datetime import datetime

import aiohttp_cors
from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckServer:
    def __init__(self, bot=None, port=8080):
        self.bot = bot
        self.port = port
        self.start_time = datetime.now()
        self.app = web.Application()
        self.setup_routes()
        self.setup_cors()

    def setup_cors(self):
        # Настройка CORS для всех маршрутов
        cors = aiohttp_cors.setup(
            self.app,
            defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*",
                )
            },
        )

        # Добавляем CORS ко всем маршрутам
        for route in list(self.app.router.routes()):
            cors.add(route)

    def setup_routes(self):
        # Health check endpoint
        self.app.router.add_get("/", self.health_check)
        self.app.router.add_get("/health", self.health_check)
        self.app.router.add_get("/status", self.bot_status)
        self.app.router.add_get("/uptime", self.uptime)

    async def health_check(self, request):
        """Простая проверка здоровья"""
        return web.json_response(
            {
                "status": "healthy",
                "service": "telegram-giveaway-bot",
                "timestamp": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
            }
        )

    async def bot_status(self, request):
        """Статус бота"""
        try:
            if self.bot:
                bot_info = await self.bot.get_me()
                return web.json_response(
                    {
                        "bot_status": "running",
                        "bot_username": bot_info.username,
                        "bot_id": bot_info.id,
                        "bot_name": bot_info.first_name,
                        "timestamp": datetime.now().isoformat(),
                    }
                )
            else:
                return web.json_response(
                    {
                        "bot_status": "not_initialized",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
        except Exception as e:
            logger.error(f"Error getting bot status: {e}")
            return web.json_response(
                {
                    "bot_status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                },
                status=500,
            )

    async def uptime(self, request):
        """Время работы сервиса"""
        uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        uptime_minutes = uptime_seconds / 60
        uptime_hours = uptime_minutes / 60
        uptime_days = uptime_hours / 24

        return web.json_response(
            {
                "start_time": self.start_time.isoformat(),
                "current_time": datetime.now().isoformat(),
                "uptime": {
                    "seconds": round(uptime_seconds, 2),
                    "minutes": round(uptime_minutes, 2),
                    "hours": round(uptime_hours, 2),
                    "days": round(uptime_days, 2),
                    "formatted": self.format_uptime(uptime_seconds),
                },
            }
        )

    def format_uptime(self, seconds):
        """Форматирование времени работы"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(
                f"{days} день"
                + ("" if days == 1 else ("а" if 2 <= days <= 4 else "ей"))
            )
        if hours > 0:
            parts.append(
                f"{hours} час"
                + ("" if hours == 1 else ("а" if 2 <= hours <= 4 else "ов"))
            )
        if minutes > 0:
            parts.append(
                f"{minutes} минут"
                + ("а" if minutes == 1 else ("ы" if 2 <= minutes <= 4 else ""))
            )
        if secs > 0 or not parts:
            parts.append(
                f"{secs} секунд"
                + ("а" if secs == 1 else ("ы" if 2 <= secs <= 4 else ""))
            )

        return ", ".join(parts)

    async def start_server(self):
        """Запуск веб-сервера"""
        try:
            runner = web.AppRunner(self.app)
            await runner.setup()

            site = web.TCPSite(runner, "0.0.0.0", self.port)
            await site.start()

            logger.info(f"Health check server started on port {self.port}")
            logger.info(
                f"Health check available at: http://localhost:{self.port}/health"
            )

            return runner
        except Exception as e:
            logger.error(f"Error starting health check server: {e}")
            raise


# Standalone запуск (для тестирования)
if __name__ == "__main__":

    async def main():
        # Создаем сервер для тестирования
        server = HealthCheckServer()
        runner = await server.start_server()

        print(f"Health check server running on http://localhost:8080")
        print("Available endpoints:")
        print("  GET /         - Main health check")
        print("  GET /health   - Health check")
        print("  GET /status   - Bot status")
        print("  GET /uptime   - Service uptime")
        print("Press Ctrl+C to stop...")

        try:
            # Бесконечный цикл для поддержания работы
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await runner.cleanup()

    # Запускаем сервер
    asyncio.run(main())
