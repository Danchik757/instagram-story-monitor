# src/utils/scheduler.py
"""
Планировщик для периодической проверки stories
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config.settings import (
    CHECK_INTERVAL_HOURS,
    INTERVAL_RANDOMNESS_MINUTES,
    CATCH_UP_MODE,
    TELEGRAM_DELIVERY_MODE,
    DAILY_DIGEST_HOUR,
    DAILY_DIGEST_MINUTE,
)


class StoryScheduler:
    """Планировщик проверки stories"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.check_function: Optional[Callable] = None
        self.notification_function: Optional[Callable] = None
        self.is_running = False
        self.last_check_time: Optional[datetime] = None
        
    def set_check_function(self, func: Callable):
        """Установить функцию для проверки stories"""
        self.check_function = func

    def set_notification_function(self, func: Callable):
        """Установить функцию отложенной отправки уведомлений"""
        self.notification_function = func
        
    async def _run_check(self):
        """Выполнить проверку stories"""
        if not self.check_function:
            logger.error("Не установлена функция проверки")
            return
            
        try:
            logger.info("=== Начинаем плановую проверку stories ===")
            self.last_check_time = datetime.now()
            
            # Вызываем функцию проверки
            await self.check_function()
            
            logger.info("=== Плановая проверка завершена ===")
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении проверки: {e}")

    async def _run_daily_digest(self):
        """Отправить накопленные уведомления по ежедневному расписанию"""
        if not self.notification_function:
            logger.error("Не установлена функция отправки ежедневного дайджеста")
            return

        try:
            logger.info("=== Начинаем ежедневную отправку накопленных stories ===")
            await self.notification_function()
            logger.info("=== Ежедневная отправка завершена ===")
        except Exception as e:
            logger.error(f"Ошибка при ежедневной отправке: {e}")
    
    def _get_next_run_time(self) -> datetime:
        """Получить время следующего запуска с рандомизацией"""
        # Базовый интервал
        base_interval = timedelta(hours=CHECK_INTERVAL_HOURS)
        
        # Добавляем случайное отклонение
        randomness = timedelta(minutes=random.randint(
            -INTERVAL_RANDOMNESS_MINUTES, 
            INTERVAL_RANDOMNESS_MINUTES
        ))
        
        next_time = datetime.now() + base_interval + randomness
        
        # Избегаем ночных проверок (2:00 - 6:00)
        if 2 <= next_time.hour <= 6:
            # Переносим на 7 утра
            next_time = next_time.replace(hour=7, minute=random.randint(0, 30))
            logger.info(f"Перенесли ночную проверку на {next_time.strftime('%H:%M')}")
        
        return next_time
    
    def start(self, run_immediately: bool = True):
        """Запустить планировщик"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
            
        try:
            # Добавляем задачу с интервалом
            self.scheduler.add_job(
                self._run_check,
                trigger=IntervalTrigger(
                    hours=CHECK_INTERVAL_HOURS,
                    minutes=0,
                    jitter=INTERVAL_RANDOMNESS_MINUTES * 60  # jitter в секундах
                ),
                id='story_check',
                name='Проверка Instagram Stories',
                replace_existing=True,
                max_instances=1  # Только один экземпляр задачи
            )

            if TELEGRAM_DELIVERY_MODE == "daily_digest":
                self.scheduler.add_job(
                    self._run_daily_digest,
                    trigger=CronTrigger(
                        hour=DAILY_DIGEST_HOUR,
                        minute=DAILY_DIGEST_MINUTE,
                    ),
                    id='daily_digest',
                    name='Ежедневная отправка stories в Telegram',
                    replace_existing=True,
                    max_instances=1,
                )
            
            # Запускаем планировщик
            self.scheduler.start()
            self.is_running = True
            
            logger.success(
                f"Планировщик запущен. Проверка каждые {CHECK_INTERVAL_HOURS} часов "
                f"(±{INTERVAL_RANDOMNESS_MINUTES} минут)"
            )
            if TELEGRAM_DELIVERY_MODE == "daily_digest":
                logger.success(
                    "Ежедневная отправка включена: "
                    f"{DAILY_DIGEST_HOUR:02d}:{DAILY_DIGEST_MINUTE:02d}"
                )
            
            # Запускаем первую проверку сразу если нужно
            if run_immediately:
                logger.info("Запускаем первую проверку...")
                asyncio.create_task(self._run_check())
                
        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")
            self.is_running = False
    
    def stop(self):
        """Остановить планировщик"""
        if not self.is_running:
            return
            
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            logger.info("Планировщик остановлен")
        except Exception as e:
            logger.error(f"Ошибка остановки планировщика: {e}")
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Получить время следующего запуска"""
        if not self.is_running:
            return None
            
        job = self.scheduler.get_job('story_check')
        if job:
            return job.next_run_time
        return None

    def get_next_digest_time(self) -> Optional[datetime]:
        """Получить время следующей ежедневной отправки"""
        if not self.is_running or TELEGRAM_DELIVERY_MODE != "daily_digest":
            return None

        job = self.scheduler.get_job('daily_digest')
        if job:
            return job.next_run_time
        return None
    
    def pause(self):
        """Приостановить выполнение задач"""
        if self.is_running:
            self.scheduler.pause()
            logger.info("Планировщик приостановлен")
    
    def resume(self):
        """Возобновить выполнение задач"""
        if self.is_running:
            self.scheduler.resume()
            logger.info("Планировщик возобновлен")
    
    def run_once_after(self, minutes: int):
        """Запустить проверку один раз через N минут"""
        run_time = datetime.now() + timedelta(minutes=minutes)
        
        self.scheduler.add_job(
            self._run_check,
            trigger='date',
            run_date=run_time,
            id=f'story_check_once_{run_time.timestamp()}',
            name=f'Одноразовая проверка в {run_time.strftime("%H:%M")}',
            replace_existing=False
        )
        
        logger.info(f"Запланирована одноразовая проверка через {minutes} минут")


# Глобальный экземпляр планировщика
story_scheduler = StoryScheduler()
