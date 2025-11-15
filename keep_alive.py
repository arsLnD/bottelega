import asyncio
import logging
import time
from datetime import datetime, timedelta

import aiohttp

logger = logging.getLogger(__name__)


class UptimeMonitor:
    def __init__(self, url, interval=300, timeout=10):
        """
        Инициализация монитора времени работы

        Args:
            url: URL для ping-а (health check endpoint)
            interval: Интервал между проверками в секундах (по умолчанию 5 минут)
            timeout: Таймаут запроса в секундах
        """
        self.url = url
        self.interval = interval
        self.timeout = timeout
        self.start_time = datetime.now()
        self.last_ping = None
        self.ping_count = 0
        self.failed_pings = 0
        self.is_running = False

    async def ping_service(self):
        """Отправить ping запрос к сервису"""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                async with session.get(self.url) as response:
                    self.ping_count += 1
                    self.last_ping = datetime.now()

                    if response.status == 200:
                        logger.info(f"✅ Ping successful - Status: {response.status}")
                        return True
                    else:
                        logger.warning(f"⚠️ Ping returned status: {response.status}")
                        self.failed_pings += 1
                        return False

        except asyncio.TimeoutError:
            logger.error(f"⏰ Ping timeout after {self.timeout}s")
            self.failed_pings += 1
            return False
        except aiohttp.ClientError as e:
            logger.error(f"❌ Network error during ping: {e}")
            self.failed_pings += 1
            return False
        except Exception as e:
            logger.error(f"💥 Unexpected error during ping: {e}")
            self.failed_pings += 1
            return False

    def get_uptime_stats(self):
        """Получить статистику времени работы"""
        uptime = datetime.now() - self.start_time
        success_rate = (
            ((self.ping_count - self.failed_pings) / self.ping_count * 100)
            if self.ping_count > 0
            else 0
        )

        return {
            "start_time": self.start_time.isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": self.format_duration(uptime.total_seconds()),
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "total_pings": self.ping_count,
            "failed_pings": self.failed_pings,
            "success_rate": round(success_rate, 2),
        }

    def format_duration(self, seconds):
        """Форматировать длительность в читаемый вид"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}д")
        if hours > 0:
            parts.append(f"{hours}ч")
        if minutes > 0:
            parts.append(f"{minutes}м")
        if secs > 0 or not parts:
            parts.append(f"{secs}с")

        return " ".join(parts)

    async def start_monitoring(self):
        """Запустить мониторинг"""
        self.is_running = True
        logger.info(f"🚀 Starting uptime monitor for {self.url}")
        logger.info(f"📊 Ping interval: {self.interval} seconds")
        logger.info(f"⏱️ Request timeout: {self.timeout} seconds")

        # Первый ping сразу
        await self.ping_service()

        while self.is_running:
            try:
                await asyncio.sleep(self.interval)

                if self.is_running:  # Проверяем еще раз после сна
                    await self.ping_service()

                    # Логируем статистику каждые 10 пингов
                    if self.ping_count % 10 == 0:
                        stats = self.get_uptime_stats()
                        logger.info(
                            f"📈 Stats: {stats['total_pings']} pings, "
                            f"{stats['success_rate']}% success, "
                            f"uptime: {stats['uptime_formatted']}"
                        )

            except asyncio.CancelledError:
                logger.info("🛑 Monitoring cancelled")
                break
            except Exception as e:
                logger.error(f"💥 Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Короткая пауза при ошибке

        logger.info("🏁 Uptime monitor stopped")

    def stop_monitoring(self):
        """Остановить мониторинг"""
        self.is_running = False
        logger.info("🛑 Stopping uptime monitor...")


# Функция для использования в других модулях
async def keep_alive(url, interval=300):
    """
    Простая функция для поддержания работы сервиса

    Args:
        url: URL для ping-а
        interval: Интервал между пингами в секундах
    """
    monitor = UptimeMonitor(url, interval)

    try:
        await monitor.start_monitoring()
    except KeyboardInterrupt:
        monitor.stop_monitoring()
    except Exception as e:
        logger.error(f"Keep alive error: {e}")
        raise


# Standalone режим
if __name__ == "__main__":
    import sys

    # Настройка логирования для standalone режима
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # URL по умолчанию или из аргументов командной строки
    default_urls = [
        "http://localhost:8080/health",
        "https://your-app.railway.app/health",
        "https://your-app.render.com/health",
        "https://your-app.fly.dev/health",
    ]

    if len(sys.argv) > 1:
        ping_url = sys.argv[1]
    else:
        print("🔍 Выберите URL для мониторинга:")
        for i, url in enumerate(default_urls, 1):
            print(f"{i}. {url}")

        try:
            choice = int(input("Введите номер (1-4): ")) - 1
            ping_url = default_urls[choice]
        except (ValueError, IndexError):
            print("❌ Неверный выбор, используется localhost")
            ping_url = default_urls[0]

    # Интервал мониторинга
    if len(sys.argv) > 2:
        try:
            ping_interval = int(sys.argv[2])
        except ValueError:
            ping_interval = 300
    else:
        ping_interval = 300

    print(f"🎯 Мониторинг: {ping_url}")
    print(f"⏰ Интервал: {ping_interval} секунд")
    print("Press Ctrl+C to stop...")

    async def main():
        await keep_alive(ping_url, ping_interval)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Мониторинг остановлен пользователем")
    except Exception as e:
        print(f"💥 Ошибка: {e}")
        sys.exit(1)
