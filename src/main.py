# src/main.py
"""
Главный модуль приложения для мониторинга Instagram Stories
"""
import asyncio
import signal
import sys
from datetime import datetime
from typing import Optional
from loguru import logger
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import (
    INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, 
    TRACKED_ACCOUNTS, LOG_LEVEL, LOG_FORMAT,
    USE_VPN, DEBUG_MODE
)
from src.instagram.client import SafeInstagramClient
from src.instagram.story import StoryHandler
from src.telegram.bot import notifier_bot
from src.telegram.handlers import NotificationHandler
from src.database.db import db_manager
from src.utils.scheduler import story_scheduler
from src.utils.vpn import VPNChecker


class InstagramStoryMonitor:
    """Основной класс приложения"""
    
    def __init__(self):
        self.instagram_client: Optional[SafeInstagramClient] = None
        self.story_handler: Optional[StoryHandler] = None
        self.is_running = False
        self.check_in_progress = False
        
        # Настройка логирования
        self._setup_logging()
        
    def _setup_logging(self):
        """Настройка логирования"""
        logger.remove()  # Удаляем стандартный обработчик
        
        # Консольный вывод
        logger.add(
            sys.stderr,
            format=LOG_FORMAT,
            level=LOG_LEVEL,
            colorize=True
        )
        
        # Файл логов
        logger.add(
            "logs/bot_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="7 days",
            format=LOG_FORMAT,
            level=LOG_LEVEL,
            encoding="utf-8"
        )
        
        logger.info("Логирование настроено")
    
    async def initialize(self) -> bool:
        """Инициализация компонентов"""
        try:
            logger.info("=== Инициализация Instagram Story Monitor ===")
            
            # Проверяем VPN если требуется
            if USE_VPN:
                vpn_status = VPNChecker.check_vpn_status()
                if not vpn_status['active']:
                    logger.warning(f"VPN не активен! {vpn_status['message']}")
                    if not DEBUG_MODE:
                        logger.error("Запуск без VPN запрещен. Включите VPN и попробуйте снова.")
                        return False
                else:
                    logger.success(f"VPN активен: {vpn_status['ip']} ({vpn_status['country']})")
            
            # Инициализируем Instagram клиент
            logger.info("Инициализация Instagram клиента...")
            self.instagram_client = SafeInstagramClient(
                INSTAGRAM_USERNAME, 
                INSTAGRAM_PASSWORD
            )
            
            # Пробуем залогиниться
            if not self.instagram_client.login():
                logger.error("Не удалось войти в Instagram")
                return False
            
            logger.success("Instagram клиент инициализирован")
            
            # Создаем обработчик stories
            self.story_handler = StoryHandler(self.instagram_client)
            
            # Инициализируем Telegram бота
            logger.info("Инициализация Telegram бота...")
            if not await notifier_bot.initialize():
                logger.error("Не удалось инициализировать Telegram бота")
                return False
            
            # Запускаем polling для команд
            await notifier_bot.start_polling()
            
            logger.success("Telegram бот инициализирован")
            
            # Добавляем отслеживаемые аккаунты в БД
            for account in TRACKED_ACCOUNTS:
                db_manager.add_tracked_user(account)
            
            # Отправляем уведомление о запуске
            await notifier_bot.send_bot_started()
            
            logger.success("=== Инициализация завершена успешно ===")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации: {e}")
            return False
    
    async def check_stories_task(self):
        """Задача проверки stories"""
        if self.check_in_progress:
            logger.warning("Проверка уже выполняется, пропускаем")
            return
        
        self.check_in_progress = True
        start_time = datetime.now()
        
        try:
            logger.info(">>> Начинаем проверку stories")
            
            # Проверяем VPN
            if USE_VPN and not VPNChecker.ensure_vpn_connected():
                await NotificationHandler.send_error_notification(
                    notifier_bot, 
                    "VPN не подключен! Проверка пропущена."
                )
                return
            
            # Проверяем stories
            stats = self.story_handler.check_all_users()
            
            # Сохраняем статистику
            duration = (datetime.now() - start_time).seconds
            stats['duration_seconds'] = duration
            stats['vpn_active'] = VPNChecker.is_wireguard_active() if USE_VPN else False
            
            db_manager.save_check_history(stats)
            
            # Отправляем уведомления о новых stories
            if stats['stories_downloaded'] > 0:
                sent_count = await notifier_bot.send_pending_notifications()
                logger.info(f"Отправлено {sent_count} уведомлений")
            
            # Отправляем сводку
            await NotificationHandler.send_summary(notifier_bot, stats)
            
            logger.success(
                f">>> Проверка завершена за {duration} сек. "
                f"Найдено: {stats['stories_found']}, "
                f"Скачано: {stats['stories_downloaded']}"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при проверке stories: {e}")
            await NotificationHandler.send_error_notification(
                notifier_bot,
                f"Ошибка проверки: {str(e)}"
            )
        finally:
            self.check_in_progress = False
    
    async def run(self):
        """Запуск основного цикла"""
        if not await self.initialize():
            logger.error("Инициализация не удалась")
            return
        
        self.is_running = True
        
        # Устанавливаем функцию проверки для планировщика
        story_scheduler.set_check_function(self.check_stories_task)
        
        # Запускаем планировщик
        story_scheduler.start(run_immediately=True)
        
        try:
            # Основной цикл
            while self.is_running:
                await asyncio.sleep(1)  # Изменено с 60 на 1 для быстрой реакции
                
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
            self.is_running = False
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Корректное завершение работы"""
        logger.info("=== Завершение работы ===")
        
        self.is_running = False
        
        # Останавливаем планировщик
        story_scheduler.stop()
        
        # Закрываем Instagram клиент
        if self.instagram_client:
            self.instagram_client.close()
        
        # Останавливаем Telegram бота
        await notifier_bot.stop()
        
        logger.info("=== Работа завершена ===")
    
    def handle_signal(self, signum, frame):
        """Обработчик сигналов"""
        logger.info(f"Получен сигнал {signum}")
        self.is_running = False
        # Принудительно прерываем asyncio loop
        for task in asyncio.all_tasks():
            task.cancel()


async def main():
    """Точка входа"""
    monitor = InstagramStoryMonitor()
    
    # Устанавливаем обработчики сигналов
    signal.signal(signal.SIGINT, monitor.handle_signal)
    signal.signal(signal.SIGTERM, monitor.handle_signal)
    
    try:
        await monitor.run()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await monitor.shutdown()


if __name__ == "__main__":
    # Запускаем приложение
    asyncio.run(main())