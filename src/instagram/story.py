# src/instagram/story.py
"""
Модуль для работы со stories
"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

from config.settings import STORIES_DIR, MAX_STORIES_PER_CHECK, CATCH_UP_MODE
from src.database.db import db_manager
from .client import SafeInstagramClient


class StoryHandler:
    """Обработчик Instagram stories"""
    
    def __init__(self, instagram_client: SafeInstagramClient):
        self.client = instagram_client
        self.db = db_manager
        self.stories_dir = Path(STORIES_DIR)
        self.stories_dir.mkdir(parents=True, exist_ok=True)
        
    def process_user_stories(self, username: str) -> Tuple[int, int]:
        """
        Обработать stories одного пользователя
        Возвращает: (количество новых stories, количество скачанных)
        """
        new_count = 0
        downloaded_count = 0
        
        try:
            # Получаем stories
            stories = self.client.get_user_stories(username)
            
            if not stories:
                logger.info(f"У {username} нет активных stories")
                return 0, 0
            
            # Ограничиваем количество stories для обработки
            stories_to_process = stories[:MAX_STORIES_PER_CHECK]
            
            if len(stories) > MAX_STORIES_PER_CHECK:
                logger.warning(
                    f"У {username} {len(stories)} stories, "
                    f"обрабатываем только первые {MAX_STORIES_PER_CHECK}"
                )
            
            for story in stories_to_process:
                story_id = str(story['id'])
                
                # Проверяем, не скачивали ли уже
                if self.db.is_story_downloaded(story_id):
                    logger.debug(f"Story {story_id} уже была скачана ранее")
                    continue
                
                new_count += 1
                
                # Скачиваем story
                file_path = self.client.download_story(story, self.stories_dir)
                
                if file_path:
                    # Сохраняем в БД
                    story_data = {
                        'username': username,
                        'story_id': story_id,
                        'story_type': 'video' if story['media_type'] == 2 else 'photo',
                        'file_path': file_path,
                        'story_url': story.get('video_url') or story.get('image_url'),
                        'caption': story.get('caption')
                    }
                    
                    if self.db.save_downloaded_story(story_data):
                        downloaded_count += 1
                        logger.success(f"Story {story_id} сохранена в БД")
                    else:
                        logger.error(f"Не удалось сохранить story {story_id} в БД")
                else:
                    logger.error(f"Не удалось скачать story {story_id}")
            
            # Обновляем время последней проверки
            self.db.update_last_checked(username)
            
        except Exception as e:
            logger.error(f"Ошибка обработки stories для {username}: {e}")
        
        return new_count, downloaded_count
    
    def check_all_users(self) -> Dict[str, any]:
        """Проверить stories у всех отслеживаемых пользователей"""
        stats = {
            'users_checked': 0,
            'stories_found': 0,
            'stories_downloaded': 0,
            'errors': []
        }
        
        # Получаем список активных пользователей
        users = self.db.get_active_users()
        
        if not users:
            logger.warning("Нет пользователей для отслеживания")
            return stats
        
        logger.info(f"Начинаем проверку {len(users)} пользователей")
        
        # Если включен режим догоняния, проверяем пропущенные stories
        if CATCH_UP_MODE:
            self._catch_up_missed_stories()
        
        # Получаем stories для всех пользователей
        all_stories = self.client.get_stories_for_all_users(users)
        
        # Обрабатываем полученные stories
        for username in users:
            stats['users_checked'] += 1
            
            if username in all_stories:
                stories = all_stories[username]
                new_count, downloaded_count = self._process_stories_list(username, stories)
                stats['stories_found'] += new_count
                stats['stories_downloaded'] += downloaded_count
            else:
                logger.debug(f"Нет stories для {username}")
        
        return stats
    
    def _process_stories_list(self, username: str, stories: List[Dict]) -> Tuple[int, int]:
        """Обработать список stories"""
        new_count = 0
        downloaded_count = 0
        
        # Ограничиваем количество
        stories_to_process = stories[:MAX_STORIES_PER_CHECK]
        
        for story in stories_to_process:
            story_id = str(story['id'])
            
            if self.db.is_story_downloaded(story_id):
                continue
            
            new_count += 1
            
            # Создаем папку для пользователя
            user_dir = self.stories_dir / username
            user_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Папка для stories: {user_dir}")
            
            # Скачиваем
            file_path = self.client.download_story(story, user_dir)
            
            if file_path:
                story_data = {
                    'username': username,
                    'story_id': story_id,
                    'story_type': 'video' if story['media_type'] == 2 else 'photo',
                    'file_path': file_path,
                    'story_url': story.get('video_url') or story.get('image_url'),
                    'caption': story.get('caption')
                }
                
                if self.db.save_downloaded_story(story_data):
                    downloaded_count += 1
                    logger.success(f"Story {story_id} от {username} скачана и сохранена")
            else:
                logger.error(f"Не удалось скачать story {story_id} от {username}")
        
        if new_count > 0:
            self.db.update_last_checked(username)
        
        return new_count, downloaded_count
    
    def _catch_up_missed_stories(self):
        """Догнать пропущенные stories с последней проверки"""
        last_check = self.db.get_last_check_time()
        
        if not last_check:
            logger.info("Это первая проверка, пропускаем догоняние")
            return
        
        time_since_check = datetime.utcnow() - last_check
        
        # Если прошло больше 24 часов, не догоняем (stories исчезают через 24ч)
        if time_since_check > timedelta(hours=24):
            logger.warning(
                f"С последней проверки прошло {time_since_check.total_seconds() / 3600:.1f} часов. "
                "Stories уже исчезли, пропускаем догоняние"
            )
            return
        
        logger.info(
            f"Режим догоняния: проверяем stories за последние "
            f"{time_since_check.total_seconds() / 3600:.1f} часов"
        )
        
        # Здесь можно добавить специальную логику для догоняния
        # Но обычно достаточно просто проверить все stories как обычно
    
    def get_stats(self) -> Dict:
        """Получить статистику"""
        return self.db.get_statistics()