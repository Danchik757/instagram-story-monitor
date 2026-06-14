# src/database/db.py
"""
Менеджер для работы с базой данных
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from loguru import logger
import json

from .models import (
    TrackedUser, DownloadedStory, CheckHistory, 
    SessionData, SessionLocal, init_database
)


class DatabaseManager:
    """Класс для управления базой данных"""
    
    def __init__(self):
        init_database()
        logger.info("База данных инициализирована")
    
    def get_session(self) -> Session:
        """Получить сессию БД"""
        return SessionLocal()
    
    # Методы для работы с отслеживаемыми пользователями
    def add_tracked_user(self, username: str) -> bool:
        """Добавить пользователя для отслеживания"""
        with self.get_session() as db:
            try:
                existing = db.query(TrackedUser).filter_by(username=username).first()
                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        db.commit()
                        logger.info(f"Пользователь {username} снова активирован")
                        return True
                    logger.warning(f"Пользователь {username} уже отслеживается")
                    return False
                
                new_user = TrackedUser(username=username)
                db.add(new_user)
                db.commit()
                logger.success(f"Пользователь {username} добавлен для отслеживания")
                return True
            except Exception as e:
                logger.error(f"Ошибка добавления пользователя {username}: {e}")
                db.rollback()
                return False
    
    def remove_tracked_user(self, username: str) -> bool:
        """Удалить пользователя из отслеживания"""
        with self.get_session() as db:
            try:
                user = db.query(TrackedUser).filter_by(username=username).first()
                if user:
                    user.is_active = False
                    db.commit()
                    logger.info(f"Пользователь {username} удален из отслеживания")
                    return True
                return False
            except Exception as e:
                logger.error(f"Ошибка удаления пользователя {username}: {e}")
                db.rollback()
                return False
    
    def get_active_users(self) -> List[str]:
        """Получить список активных пользователей"""
        with self.get_session() as db:
            users = db.query(TrackedUser).filter_by(is_active=True).all()
            return [user.username for user in users]
    
    def update_last_checked(self, username: str) -> None:
        """Обновить время последней проверки"""
        with self.get_session() as db:
            user = db.query(TrackedUser).filter_by(username=username).first()
            if user:
                user.last_checked = datetime.utcnow()
                db.commit()
    
    # Методы для работы со stories
    def is_story_downloaded(self, story_id: str) -> bool:
        """Проверить, скачана ли уже story"""
        with self.get_session() as db:
            return db.query(DownloadedStory).filter_by(story_id=story_id).first() is not None
    
    def save_downloaded_story(self, story_data: Dict) -> bool:
        """Сохранить информацию о скачанной story"""
        with self.get_session() as db:
            try:
                story = DownloadedStory(
                    username=story_data['username'],
                    story_id=story_data['story_id'],
                    story_type=story_data['story_type'],
                    file_path=story_data['file_path'],
                    story_url=story_data.get('story_url'),
                    caption=story_data.get('caption')
                )
                db.add(story)
                db.commit()
                logger.debug(f"Story {story_data['story_id']} сохранена в БД")
                return True
            except Exception as e:
                logger.error(f"Ошибка сохранения story: {e}")
                db.rollback()
                return False
    
    def get_unnotified_stories(self) -> List[DownloadedStory]:
        """Получить stories, о которых еще не уведомили"""
        with self.get_session() as db:
            return db.query(DownloadedStory).filter_by(notified=False).order_by(
                DownloadedStory.downloaded_at.asc()
            ).all()

    def count_unnotified_stories(self) -> int:
        """Получить количество накопленных неотправленных stories"""
        with self.get_session() as db:
            return db.query(DownloadedStory).filter_by(notified=False).count()
    
    def mark_story_notified(self, story_id: str) -> None:
        """Отметить story как отправленную"""
        with self.get_session() as db:
            story = db.query(DownloadedStory).filter_by(story_id=story_id).first()
            if story:
                story.notified = True
                story.notified_at = datetime.utcnow()
                db.commit()
    
    def get_stories_after_timestamp(self, username: str, timestamp: datetime) -> List[DownloadedStory]:
        """Получить stories пользователя после определенного времени"""
        with self.get_session() as db:
            return db.query(DownloadedStory).filter(
                DownloadedStory.username == username,
                DownloadedStory.downloaded_at > timestamp
            ).order_by(DownloadedStory.downloaded_at.desc()).all()
    
    # Методы для работы с историей проверок
    def save_check_history(self, check_data: Dict) -> None:
        """Сохранить информацию о проверке"""
        with self.get_session() as db:
            try:
                # Конвертируем список ошибок в строку
                errors_str = json.dumps(check_data.get('errors', [])) if check_data.get('errors') else None
                
                history = CheckHistory(
                    users_checked=check_data.get('users_checked', 0),
                    stories_found=check_data.get('stories_found', 0),
                    stories_downloaded=check_data.get('stories_downloaded', 0),
                    errors=errors_str,  # Изменено
                    vpn_active=check_data.get('vpn_active', False),
                    duration_seconds=check_data.get('duration_seconds')
                )
                db.add(history)
                db.commit()
            except Exception as e:
                logger.error(f"Ошибка сохранения истории проверки: {e}")
                db.rollback()
    
    def get_last_check_time(self) -> Optional[datetime]:
        """Получить время последней проверки"""
        with self.get_session() as db:
            last_check = db.query(CheckHistory).order_by(
                CheckHistory.checked_at.desc()
            ).first()
            return last_check.checked_at if last_check else None
    
    # Методы для работы с сессиями Instagram
    def save_instagram_session(self, username: str, session_data: str, device_id: str = None) -> None:
        """Сохранить сессию Instagram"""
        with self.get_session() as db:
            try:
                existing = db.query(SessionData).filter_by(username=username).first()
                if existing:
                    existing.session_data = session_data
                    existing.device_id = device_id
                    existing.last_used = datetime.utcnow()
                    existing.is_valid = True
                else:
                    new_session = SessionData(
                        username=username,
                        session_data=session_data,
                        device_id=device_id
                    )
                    db.add(new_session)
                db.commit()
                logger.debug(f"Сессия для {username} сохранена")
            except Exception as e:
                logger.error(f"Ошибка сохранения сессии: {e}")
                db.rollback()
    
    def get_instagram_session(self, username: str) -> Optional[Dict]:
        """Получить сохраненную сессию Instagram"""
        with self.get_session() as db:
            session = db.query(SessionData).filter_by(
                username=username, 
                is_valid=True
            ).first()
            if session:
                session.last_used = datetime.utcnow()
                db.commit()
                return {
                    'session_data': session.session_data,
                    'device_id': session.device_id
                }
            return None
    
    def invalidate_session(self, username: str) -> None:
        """Пометить сессию как невалидную"""
        with self.get_session() as db:
            session = db.query(SessionData).filter_by(username=username).first()
            if session:
                session.is_valid = False
                db.commit()
    
    # Статистика
    def get_statistics(self) -> Dict:
        """Получить статистику работы бота"""
        with self.get_session() as db:
            total_users = db.query(TrackedUser).filter_by(is_active=True).count()
            total_stories = db.query(DownloadedStory).count()
            
            # Stories за последние 24 часа
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_stories = db.query(DownloadedStory).filter(
                DownloadedStory.downloaded_at > yesterday
            ).count()
            
            # Последняя проверка
            last_check = self.get_last_check_time()
            
            return {
                'total_users': total_users,
                'total_stories': total_stories,
                'recent_stories': recent_stories,
                'last_check': last_check
            }


# Создаем глобальный экземпляр менеджера
db_manager = DatabaseManager()
