# src/database/models.py
"""
Модели базы данных для хранения информации о stories
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import DATABASE_PATH

Base = declarative_base()

class TrackedUser(Base):
    """Отслеживаемые пользователи Instagram"""
    __tablename__ = 'tracked_users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    stories_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<TrackedUser(username='{self.username}', active={self.is_active})>"


class DownloadedStory(Base):
    """Скачанные stories"""
    __tablename__ = 'downloaded_stories'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    story_id = Column(String(100), unique=True, nullable=False)
    story_type = Column(String(20), nullable=False)  # 'photo' или 'video'
    file_path = Column(String(500), nullable=False)
    story_url = Column(Text, nullable=True)
    caption = Column(Text, nullable=True)
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    notified = Column(Boolean, default=False)
    notified_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<DownloadedStory(username='{self.username}', id='{self.story_id}')>"


class CheckHistory(Base):
    """История проверок"""
    __tablename__ = 'check_history'
    
    id = Column(Integer, primary_key=True)
    checked_at = Column(DateTime, default=datetime.utcnow)
    users_checked = Column(Integer, default=0)
    stories_found = Column(Integer, default=0)
    stories_downloaded = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    vpn_active = Column(Boolean, default=False)
    duration_seconds = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f"<CheckHistory(checked_at='{self.checked_at}', stories={self.stories_found})>"


class SessionData(Base):
    """Сохраненные сессии Instagram"""
    __tablename__ = 'instagram_sessions'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    session_data = Column(Text, nullable=False)
    device_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, default=datetime.utcnow)
    is_valid = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<SessionData(username='{self.username}', valid={self.is_valid})>"


# Создание движка и сессии
engine = create_engine(f'sqlite:///{DATABASE_PATH}', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_database():
    """Инициализация базы данных"""
    Base.metadata.create_all(bind=engine)
    
def get_db():
    """Получить сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()