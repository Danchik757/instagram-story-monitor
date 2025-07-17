# src/telegram/bot.py
"""
Telegram бот для отправки уведомлений о новых stories
"""
import asyncio
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from telegram import Bot, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes
from loguru import logger

from config.settings import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, MESSAGES, 
    TRACKED_ACCOUNTS, MAX_FILE_SIZE_MB
)
from src.database.db import db_manager


class StoryNotifierBot:
    """Telegram бот для уведомлений о stories"""
    
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.chat_id = TELEGRAM_CHAT_ID
        self.db = db_manager
        self.application = None
        
    async def initialize(self):
        """Инициализация бота"""
        try:
            # Создаем application
            self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Добавляем обработчики команд
            self.application.add_handler(CommandHandler("start", self.cmd_start))
            self.application.add_handler(CommandHandler("status", self.cmd_status))
            self.application.add_handler(CommandHandler("stats", self.cmd_stats))
            self.application.add_handler(CommandHandler("users", self.cmd_users))
            self.application.add_handler(CommandHandler("add", self.cmd_add_user))
            self.application.add_handler(CommandHandler("remove", self.cmd_remove_user))
            self.application.add_handler(CommandHandler("help", self.cmd_help))
            self.application.add_handler(CommandHandler("channels", self.cmd_channels))
            self.application.add_handler(CommandHandler("add_channel", self.cmd_add_channel))
            
            # Инициализируем бота
            await self.application.initialize()
            
            logger.success("Telegram бот инициализирован")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {e}")
            return False
    
    async def send_message(self, text: str, parse_mode: str = ParseMode.MARKDOWN) -> bool:
        """Отправить текстовое сообщение"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except TelegramError as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
            return False
    
    async def send_photo(self, photo_path: str, caption: Optional[str] = None) -> bool:
        """Отправить фото"""
        try:
            file_path = Path(photo_path)
            if not file_path.exists():
                logger.error(f"Файл не найден: {photo_path}")
                return False
            
            # Проверяем размер файла
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.warning(f"Файл слишком большой: {file_size_mb:.1f} MB")
                return False
            
            with open(file_path, 'rb') as photo:
                await self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
            return True
            
        except TelegramError as e:
            logger.error(f"Ошибка отправки фото: {e}")
            return False
    
    async def send_video(self, video_path: str, caption: Optional[str] = None) -> bool:
        """Отправить видео"""
        try:
            file_path = Path(video_path)
            if not file_path.exists():
                logger.error(f"Файл не найден: {video_path}")
                return False
            
            # Проверяем размер файла
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                logger.warning(f"Файл слишком большой: {file_size_mb:.1f} MB")
                # Отправляем только уведомление без файла
                await self.send_message(
                    f"{caption}\n\n⚠️ Видео слишком большое ({file_size_mb:.1f} MB)"
                )
                return True
            
            with open(file_path, 'rb') as video:
                await self.bot.send_video(
                    chat_id=self.chat_id,
                    video=video,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN,
                    supports_streaming=True
                )
            return True
            
        except TelegramError as e:
            logger.error(f"Ошибка отправки видео: {e}")
            return False
    
    async def send_story_notification(self, story_data: dict) -> bool:
        """Отправить уведомление о новой story"""
        try:
            username = story_data['username']
            file_path = story_data['file_path']
            caption_text = story_data.get('caption', '')
            story_type = story_data['story_type']
            
            # Формируем подпись
            caption = MESSAGES['new_story'].format(username=username)
            if caption_text:
                caption += f"\n\n📝 {caption_text[:200]}"  # Ограничиваем длину
            
            caption += f"\n\n🕐 {datetime.now().strftime('%H:%M')}"
            
            # Отправляем в зависимости от типа
            if story_type == 'photo':
                success = await self.send_photo(file_path, caption)
            else:  # video
                success = await self.send_video(file_path, caption)
            
            if success:
                # Отмечаем как отправленное
                self.db.mark_story_notified(story_data['story_id'])
                logger.success(f"Уведомление о story {story_data['story_id']} отправлено")
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о story: {e}")
            return False
    
    async def send_pending_notifications(self) -> int:
        """Отправить все ожидающие уведомления"""
        pending_stories = self.db.get_unnotified_stories()
        sent_count = 0
        
        for story in pending_stories:
            story_data = {
                'username': story.username,
                'story_id': story.story_id,
                'story_type': story.story_type,
                'file_path': story.file_path,
                'caption': story.caption
            }
            
            if await self.send_story_notification(story_data):
                sent_count += 1
                
            # Небольшая задержка между отправками
            await asyncio.sleep(1)
        
        return sent_count
    
    async def send_bot_started(self):
        """Отправить уведомление о запуске бота"""
        accounts_list = ", ".join(TRACKED_ACCOUNTS)
        message = f"✅ Бот запущен и мониторит аккаунты: {accounts_list}"
        await self.send_message(message, parse_mode=None)
    
    async def send_check_completed(self, stories_count: int):
        """Отправить уведомление о завершении проверки"""
        if stories_count > 0:
            message = MESSAGES['check_completed'].format(count=stories_count)
            await self.send_message(message)
    
    # Команды бота
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        welcome_text = (
            "👋 Привет! Я бот для отслеживания Instagram Stories.\n\n"
            "Я буду присылать тебе уведомления о новых stories от выбранных аккаунтов.\n\n"
            "Доступные команды:\n"
            "/status - Текущий статус\n"
            "/stats - Статистика\n"
            "/users - Список отслеживаемых аккаунтов\n"
            "/help - Помощь"
        )
        await update.message.reply_text(welcome_text)
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status"""
        stats = self.db.get_statistics()
        last_check = stats['last_check']
        
        if last_check:
            time_ago = datetime.utcnow() - last_check
            hours = int(time_ago.total_seconds() / 3600)
            minutes = int((time_ago.total_seconds() % 3600) / 60)
            last_check_str = f"{hours}ч {minutes}м назад"
        else:
            last_check_str = "Еще не было"
        
        status_text = (
            "📊 *Статус бота*\n\n"
            f"✅ Бот работает\n"
            f"👥 Отслеживается аккаунтов: {stats['total_users']}\n"
            f"🕐 Последняя проверка: {last_check_str}\n"
            f"📸 Stories за 24ч: {stats['recent_stories']}"
        )
        
        await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats"""
        stats = self.db.get_statistics()
        
        stats_text = (
            "📈 *Статистика*\n\n"
            f"📸 Всего stories скачано: {stats['total_stories']}\n"
            f"👥 Активных аккаунтов: {stats['total_users']}\n"
            f"🕐 Stories за последние 24ч: {stats['recent_stories']}"
        )
        
        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /users"""
        users = self.db.get_active_users()
        
        if users:
            users_list = "\n".join([f"• @{user}" for user in users])
            text = f"👥 *Отслеживаемые аккаунты:*\n\n{users_list}"
        else:
            text = "❌ Нет отслеживаемых аккаунтов"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def cmd_add_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /add username"""
        if not context.args:
            await update.message.reply_text(
                "Использование: /add username\n"
                "Пример: /add friend_username"
            )
            return
        
        username = context.args[0].replace('@', '')
        
        if self.db.add_tracked_user(username):
            await update.message.reply_text(f"✅ Пользователь @{username} добавлен")
        else:
            await update.message.reply_text(f"❌ Пользователь @{username} уже отслеживается")
    
    async def cmd_remove_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /remove username"""
        if not context.args:
            await update.message.reply_text(
                "Использование: /remove username\n"
                "Пример: /remove friend_username"
            )
            return
        
        username = context.args[0].replace('@', '')
        
        if self.db.remove_tracked_user(username):
            await update.message.reply_text(f"✅ Пользователь @{username} удален")
        else:
            await update.message.reply_text(f"❌ Пользователь @{username} не найден")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = (
            "📚 *Помощь*\n\n"
            "Доступные команды:\n"
            "/start - Приветствие\n"
            "/status - Текущий статус бота\n"
            "/stats - Статистика скачанных stories\n"
            "/users - Список отслеживаемых аккаунтов\n"
            "/add username - Добавить аккаунт\n"
            "/remove username - Удалить аккаунт\n"
            "/help - Эта справка\n\n"
            f"Бот проверяет stories каждые {TRACKED_ACCOUNTS} часа"
        )
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def start_polling(self):
        """Запустить polling для команд"""
        if self.application:
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot polling запущен")
    
    async def stop(self):
        """Остановить бота"""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            logger.info("Telegram бот остановлен")

    async def cmd_channels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /channels - список отслеживаемых каналов"""
        if MONITORED_CHANNELS:
            channels_list = "\n".join([f"• @{ch}" for ch in MONITORED_CHANNELS])
            text = f"📢 *Отслеживаемые Telegram каналы:*\n\n{channels_list}"
        else:
            text = "❌ Нет отслеживаемых Telegram каналов"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

    async def cmd_add_channel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /add_channel channelname"""
        if not context.args:
            await update.message.reply_text(
                "Использование: /add_channel @channelname\n"
                "Пример: /add_channel @durov"
            )
            return
        
        channel = context.args[0].replace('@', '')
        # Здесь можно добавить логику добавления канала
        await update.message.reply_text(f"Канал @{channel} будет проверяться")

# Глобальный экземпляр бота
notifier_bot = StoryNotifierBot()