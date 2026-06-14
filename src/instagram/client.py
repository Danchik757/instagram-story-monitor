# src/instagram/client.py
"""
Instagram клиент с максимальной защитой от обнаружения
"""
import os
import json
import pickle
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime, timedelta
import random
import time

from instagrapi import Client
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, 
    TwoFactorRequired, PleaseWaitFewMinutes
)
from loguru import logger

from .safety import InstagramSafety
safety = InstagramSafety()


class SafeInstagramClient:
    """Безопасный клиент для работы с Instagram"""
    
    def __init__(
        self,
        username: str,
        password: str,
        session_dir: str = "./data/sessions",
        proxy_url: Optional[str] = None,
    ):
        self.username = username
        self.password = password
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / f"{username}.json"
        self.proxy_url = proxy_url
        
        self.client = None
        self.safety = InstagramSafety()
        self.is_logged_in = False
        self.last_story_check = {}
        
    def _get_session_settings(self) -> Optional[dict]:
        """Загрузить сохраненную сессию"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки сессии: {e}")
                self.session_file.unlink()
        return None
    
    def _save_session(self) -> None:
        """Сохранить текущую сессию"""
        if self.client:
            try:
                settings = self.client.get_settings()
                with open(self.session_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                logger.info("Сессия сохранена")
            except Exception as e:
                logger.error(f"Ошибка сохранения сессии: {e}")
    
    @safety.safe_action
    def login(self, force_login: bool = False) -> bool:
        """Безопасный вход в Instagram"""
        try:
            self.client = Client()
            if self.proxy_url:
                self.client.set_proxy(self.proxy_url)
                logger.info(f"Instagram клиент использует proxy {self.proxy_url}")
            
            # Настройки для обхода детекции
            self.client.delay_range = [1, 3]
            
            # Генерируем device_id на основе username
            device_id = self.safety.generate_device_id(self.username)
            
            # Попытка входа через сохраненную сессию
            if not force_login:
                session = self._get_session_settings()
                if session:
                    try:
                        self.client.set_settings(session)
                        self.client.login(self.username, self.password)
                        
                        logger.success("Вход выполнен через сохраненную сессию")
                        self.is_logged_in = True
                        
                        # Имитируем поведение после входа
                        self.safety.simulate_app_behavior()
                        
                        return True
                    except LoginRequired:
                        logger.warning("Сессия устарела, требуется повторный вход")
                        self.session_file.unlink()
                    except Exception as e:
                        logger.warning(f"Ошибка при использовании сессии: {e}")
            
            # Обычный вход
            logger.info("Выполняем вход с логином и паролем")
            
            try:
                self.client.login(self.username, self.password)
                
                logger.success("Вход выполнен успешно")
                self.is_logged_in = True
                
                # Сохраняем сессию
                self._save_session()
                
                # Имитируем поведение после входа
                self.safety.simulate_app_behavior()
                
                return True
                
            except TwoFactorRequired:
                logger.error("Требуется двухфакторная аутентификация. Отключите её временно в настройках Instagram")
                return False
                
            except ChallengeRequired as e:
                logger.error(f"Instagram запросил подтверждение через SMS/Email. Войдите через браузер и подтвердите это устройство")
                return False
                
            except PleaseWaitFewMinutes:
                logger.error("Instagram просит подождать. Слишком много попыток.")
                self.safety.exponential_backoff(attempt=3)
                return False
                
        except Exception as e:
            logger.error(f"Ошибка входа: {e}")
            return False
    
    def ensure_logged_in(self) -> bool:
        """Убедиться что залогинены"""
        if not self.is_logged_in:
            return self.login()
        
        try:
            # Проверяем валидность сессии
            self.client.get_timeline_feed()
            return True
        except LoginRequired:
            logger.warning("Сессия истекла, выполняем повторный вход")
            return self.login(force_login=True)
        except Exception as e:
            logger.error(f"Ошибка проверки сессии: {e}")
            return self.login(force_login=True)
    
    @safety.safe_action
    def get_user_stories(self, username: str) -> List[Dict]:
        """Получить stories пользователя"""
        if not self.ensure_logged_in():
            return []
        
        try:
            # Получаем user_id
            user_info = self.client.user_info_by_username(username)
            if not user_info:
                logger.warning(f"Пользователь {username} не найден")
                return []
            
            user_id = user_info.pk
            
            # Получаем stories
            stories = []
            try:
                user_stories = self.client.user_stories(user_id)
                
                for story in user_stories:
                    story_data = {
                        'id': story.pk,
                        'code': story.code,
                        'taken_at': story.taken_at,
                        'media_type': story.media_type,  # 1 - фото, 2 - видео
                        'thumbnail_url': story.thumbnail_url if story.media_type == 2 else story.image_versions2['candidates'][0]['url'],
                        'video_url': story.video_url if story.media_type == 2 else None,
                        'image_url': story.image_versions2['candidates'][0]['url'] if story.media_type == 1 else None,
                        'caption': story.caption_text if hasattr(story, 'caption_text') else None,
                        'user': {
                            'username': username,
                            'full_name': user_info.full_name
                        }
                    }
                    stories.append(story_data)
                
                logger.info(f"Найдено {len(stories)} stories у {username}")
                return stories
                
            except Exception as e:
                logger.error(f"Ошибка получения stories для {username}: {e}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка при работе с пользователем {username}: {e}")
            return []
    
    @safety.safe_action
    def download_story(self, story_data: Dict, save_path: Path) -> Optional[str]:
        """Скачать story"""
        if not self.ensure_logged_in():
            return None
        
        try:
            story_id = story_data['id']
            media_type = story_data['media_type']
            
            # Определяем расширение файла
            extension = '.mp4' if media_type == 2 else '.jpg'
            filename = f"{story_data['user']['username']}_{story_id}{extension}"
            file_path = save_path / filename
            
            # Путь без расширения для instagrapi
            file_path_no_ext = save_path / f"{story_data['user']['username']}_{story_id}"
            
            # Скачиваем
            if media_type == 2:  # Видео
                video_url = story_data['video_url']
                if video_url:
                    self.client.video_download_by_url(video_url, filename=str(file_path_no_ext))
            else:  # Фото
                image_url = story_data['image_url']
                if image_url:
                    self.client.photo_download_by_url(image_url, filename=str(file_path_no_ext))
            
            # Проверяем, что файл создан
            if file_path.exists():
                logger.success(f"Story {story_id} скачана: {filename}")
                return str(file_path)
            else:
                logger.error(f"Файл {filename} не был создан")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка скачивания story {story_data['id']}: {e}")
            return None
    
    def get_stories_for_all_users(self, usernames: List[str]) -> Dict[str, List[Dict]]:
        """Получить stories для всех пользователей"""
        all_stories = {}
        
        # Проверяем, можем ли делать проверку
        optimal, reason = self.safety.get_optimal_check_time()
        if not optimal and "Ночное время" in reason:
            logger.info(f"Пропускаем проверку: {reason}")
            return all_stories
        
        # Перемешиваем порядок проверки
        shuffled_users = usernames.copy()
        random.shuffle(shuffled_users)
        
        for i, username in enumerate(shuffled_users):
            # Пропускаем некоторых пользователей для случайности
            # if self.safety.should_skip_check() and i > 0:
            #     logger.info(f"Пропускаем проверку {username} для имитации нерегулярности")
            #     continue
            
            # Проверяем лимиты сессии
            if not self.safety.check_session_limits():
                logger.warning("Достигнуты лимиты сессии, прерываем проверку")
                break
            
            logger.info(f"Проверяем stories у {username}")
            stories = self.get_user_stories(username)
            
            if stories:
                all_stories[username] = stories
            
            # Задержка между пользователями
            if i < len(shuffled_users) - 1:
                delay = random.uniform(30, 90)
                logger.debug(f"Пауза между пользователями: {delay:.0f} сек")
                time.sleep(delay)
        
        return all_stories
    
    def close(self):
        """Закрыть клиент"""
        if self.client:
            try:
                self._save_session()
            except:
                pass
            self.is_logged_in = False
            logger.info("Instagram клиент закрыт")
