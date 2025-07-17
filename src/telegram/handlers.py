# src/telegram/handlers.py
"""
Дополнительные обработчики для Telegram бота
"""
from typing import Dict, List
from datetime import datetime
from loguru import logger

from config.settings import MESSAGES
from src.database.db import db_manager


class NotificationHandler:
    """Обработчик уведомлений"""
    
    @staticmethod
    async def format_story_message(story_data: Dict) -> str:
        """Форматировать сообщение о story"""
        username = story_data['username']
        caption = story_data.get('caption', '')
        story_type = "📸 Фото" if story_data['story_type'] == 'photo' else "🎥 Видео"
        
        message = f"🆕 Новая история от @{username}\n"
        message += f"{story_type}\n"
        
        if caption:
            # Обрезаем длинные подписи
            if len(caption) > 200:
                caption = caption[:197] + "..."
            message += f"\n💬 {caption}\n"
        
        message += f"\n🕐 {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    @staticmethod
    def batch_notifications(stories: List[Dict]) -> List[str]:
        """Группировать уведомления по пользователям"""
        # Группируем по username
        grouped = {}
        for story in stories:
            username = story['username']
            if username not in grouped:
                grouped[username] = []
            grouped[username].append(story)
        
        messages = []
        for username, user_stories in grouped.items():
            if len(user_stories) == 1:
                # Одна story - обычное сообщение
                messages.append(NotificationHandler.format_story_message(user_stories[0]))
            else:
                # Несколько stories - групповое сообщение
                message = f"🆕 {len(user_stories)} новых историй от @{username}\n"
                message += f"\n🕐 {datetime.now().strftime('%H:%M:%S')}"
                messages.append(message)
        
        return messages
    
    @staticmethod
    async def send_error_notification(bot, error_text: str):
        """Отправить уведомление об ошибке"""
        message = MESSAGES['error'].format(error=error_text)
        try:
            await bot.send_message(message)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление об ошибке: {e}")
    
    @staticmethod
    async def send_summary(bot, stats: Dict):
        """Отправить сводку о проверке"""
        if stats['stories_downloaded'] == 0:
            return  # Не отправляем если нет новых stories
        
        message = (
            f"✅ Проверка завершена\n\n"
            f"👥 Проверено аккаунтов: {stats['users_checked']}\n"
            f"📸 Найдено новых stories: {stats['stories_found']}\n"
            f"💾 Скачано: {stats['stories_downloaded']}"
        )
        
        if stats.get('errors'):
            message += f"\n\n⚠️ Были ошибки: {len(stats['errors'])}"
        
        try:
            await bot.send_message(message)
        except Exception as e:
            logger.error(f"Не удалось отправить сводку: {e}")