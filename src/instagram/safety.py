# src/instagram/safety.py
"""
Модуль для защиты от блокировки Instagram аккаунта
"""
import time
import random
import functools
from typing import Callable, Any
from fake_useragent import UserAgent
from loguru import logger
import hashlib
import json
from datetime import datetime, timedelta

class InstagramSafety:
    """Класс для обеспечения безопасности при работе с Instagram"""
    
    def __init__(self, min_delay: int = 15, max_delay: int = 45):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.ua = UserAgent()
        self.last_action_time = None
        self.action_count = 0
        self.session_start = datetime.now()
        
    def get_random_user_agent(self) -> str:
        """Получить случайный User-Agent мобильного устройства"""
        mobile_agents = [
            'Instagram 267.0.0.25.121 Android (30/11; 480dpi; 1080x2340; Xiaomi/Redmi; Redmi Note 8 Pro; begonia; mt6785)',
            'Instagram 267.0.0.25.121 Android (31/12; 480dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100)',
            'Instagram 267.0.0.25.121 Android (30/11; 420dpi; 1080x2186; Google/google; Pixel 5; redfin; redfin)',
            'Instagram 267.0.0.25.121 Android (29/10; 480dpi; 1080x2265; OnePlus; GM1913; OnePlus7Pro; msmnile)',
        ]
        return random.choice(mobile_agents)
    
    def random_delay(self, min_sec: int = None, max_sec: int = None) -> None:
        """Случайная задержка между действиями"""
        min_delay = min_sec or self.min_delay
        max_delay = max_sec or self.max_delay
        
        # Добавляем вариативность
        delay = random.uniform(min_delay, max_delay)
        
        # Иногда делаем микро-паузы (имитация чтения)
        if random.random() < 0.3:
            delay += random.uniform(0.5, 2.5)
            
        logger.debug(f"Задержка {delay:.2f} секунд")
        time.sleep(delay)
    
    def human_like_delay(self, action_type: str = "default") -> None:
        """Задержка, имитирующая человеческое поведение"""
        delays = {
            "login": (5, 10),
            "story_view": (3, 8),
            "story_download": (2, 5),
            "navigation": (1, 3),
            "scroll": (0.5, 2),
            "default": (self.min_delay, self.max_delay)
        }
        
        min_d, max_d = delays.get(action_type, delays["default"])
        
        # Добавляем "усталость" - чем дольше сессия, тем медленнее действия
        session_duration = (datetime.now() - self.session_start).seconds / 3600  # в часах
        fatigue_factor = 1 + (session_duration * 0.1)  # +10% за каждый час
        
        self.random_delay(min_d * fatigue_factor, max_d * fatigue_factor)
    
    def safe_action(self, func: Callable) -> Callable:
        """Декоратор для безопасного выполнения действий"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Проверяем частоту действий
            if self.last_action_time:
                time_since_last = (datetime.now() - self.last_action_time).seconds
                if time_since_last < self.min_delay:
                    wait_time = self.min_delay - time_since_last
                    logger.warning(f"Слишком частые действия, ждем {wait_time} сек")
                    time.sleep(wait_time)
            
            # Добавляем случайную задержку перед действием
            self.human_like_delay(func.__name__)
            
            try:
                result = func(*args, **kwargs)
                self.action_count += 1
                self.last_action_time = datetime.now()
                
                # Длинная пауза каждые 10-15 действий
                if self.action_count % random.randint(10, 15) == 0:
                    pause_time = random.uniform(60, 180)
                    logger.info(f"Делаем длинную паузу {pause_time:.0f} сек (имитация отдыха)")
                    time.sleep(pause_time)
                
                return result
            except Exception as e:
                logger.error(f"Ошибка в {func.__name__}: {e}")
                # Экспоненциальная задержка при ошибках
                self.exponential_backoff()
                raise
        
        return wrapper
    
    def exponential_backoff(self, attempt: int = 1, max_delay: int = 300) -> None:
        """Экспоненциальная задержка при ошибках"""
        delay = min(2 ** attempt + random.uniform(0, 1), max_delay)
        logger.warning(f"Экспоненциальная задержка: {delay:.1f} сек (попытка {attempt})")
        time.sleep(delay)
    
    def check_session_limits(self) -> bool:
        """Проверка лимитов текущей сессии"""
        session_duration = (datetime.now() - self.session_start).seconds / 3600
        
        # Ограничения
        if session_duration > 2:  # 2 часа
            logger.warning("Сессия длится больше 2 часов, рекомендуется перерыв")
            return False
            
        if self.action_count > 50:  # 50 действий за сессию
            logger.warning("Превышен лимит действий за сессию")
            return False
            
        return True
    
    def generate_device_id(self, seed: str) -> str:
        """Генерация постоянного device_id для аккаунта"""
        return hashlib.md5(seed.encode()).hexdigest()
    
    def get_random_location(self) -> dict:
        """Получить случайную, но постоянную локацию"""
        locations = [
            {"lat": 55.7558, "lng": 37.6173, "name": "Moscow"},
            {"lat": 59.9311, "lng": 30.3609, "name": "Saint Petersburg"},
            {"lat": 53.9006, "lng": 27.5590, "name": "Minsk"},
            {"lat": 50.4501, "lng": 30.5234, "name": "Kyiv"},
        ]
        return random.choice(locations)
    
    def simulate_app_behavior(self) -> None:
        """Имитация поведения мобильного приложения"""
        behaviors = [
            lambda: logger.debug("Имитация свайпа вниз"),
            lambda: logger.debug("Имитация просмотра ленты"),
            lambda: logger.debug("Имитация проверки уведомлений"),
            lambda: time.sleep(random.uniform(0.5, 2)),
        ]
        
        # Выполняем 1-3 случайных действия
        for _ in range(random.randint(1, 3)):
            action = random.choice(behaviors)
            action()
            self.random_delay(1, 3)
    
    def should_skip_check(self) -> bool:
        """Определить, нужно ли пропустить текущую проверку"""
        # 10% шанс пропустить проверку (имитация нерегулярности)
        if random.random() < 0.1:
            logger.info("Пропускаем проверку для имитации нерегулярности")
            return True
        return False
    
    def get_optimal_check_time(self) -> tuple:
        """Получить оптимальное время для проверки"""
        # Избегаем проверок ночью (2:00 - 6:00)
        current_hour = datetime.now().hour
        if 2 <= current_hour <= 6:
            return False, "Ночное время, откладываем проверку"
        
        # Лучшее время: утро (7-9), обед (12-14), вечер (18-22)
        optimal_hours = list(range(7, 10)) + list(range(12, 15)) + list(range(18, 23))
        if current_hour in optimal_hours:
            return True, "Оптимальное время для проверки"
        
        return True, "Обычное время"

# Использование в основном коде:
safety = InstagramSafety(min_delay=15, max_delay=45)