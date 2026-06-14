# config/settings.py
"""
Конфигурация приложения
"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
STORIES_DIR = DATA_DIR / "stories"
SESSIONS_DIR = DATA_DIR / "sessions"
DATABASE_PATH = DATA_DIR / "bot.db"

# Создаем директории если их нет
for directory in [DATA_DIR, LOGS_DIR, STORIES_DIR, SESSIONS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Instagram настройки
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
    raise ValueError("Необходимо указать INSTAGRAM_USERNAME и INSTAGRAM_PASSWORD в .env файле")

# Telegram настройки
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise ValueError("Необходимо указать TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env файле")

# Преобразуем chat_id в int
try:
    TELEGRAM_CHAT_ID = int(TELEGRAM_CHAT_ID)
except ValueError:
    raise ValueError("TELEGRAM_CHAT_ID должен быть числом")

# Отслеживаемые аккаунты
TRACKED_ACCOUNTS_STR = os.getenv("TRACKED_ACCOUNTS", "")
TRACKED_ACCOUNTS: List[str] = [
    acc.strip() for acc in TRACKED_ACCOUNTS_STR.split(",") if acc.strip()
]

if not TRACKED_ACCOUNTS:
    raise ValueError("Необходимо указать хотя бы один аккаунт в TRACKED_ACCOUNTS")

# Интервалы проверки
CHECK_INTERVAL_HOURS = float(os.getenv("CHECK_INTERVAL_HOURS", "4"))
INTERVAL_RANDOMNESS_MINUTES = int(os.getenv("INTERVAL_RANDOMNESS_MINUTES", "30"))

# Режим доставки в Telegram
TELEGRAM_DELIVERY_MODE = os.getenv("TELEGRAM_DELIVERY_MODE", "immediate").strip().lower()
if TELEGRAM_DELIVERY_MODE not in {"immediate", "daily_digest"}:
    raise ValueError(
        "TELEGRAM_DELIVERY_MODE должен быть 'immediate' или 'daily_digest'"
    )

DAILY_DIGEST_TIME = os.getenv("DAILY_DIGEST_TIME", "21:00").strip()
try:
    DAILY_DIGEST_HOUR_STR, DAILY_DIGEST_MINUTE_STR = DAILY_DIGEST_TIME.split(":", maxsplit=1)
    DAILY_DIGEST_HOUR = int(DAILY_DIGEST_HOUR_STR)
    DAILY_DIGEST_MINUTE = int(DAILY_DIGEST_MINUTE_STR)
except ValueError as exc:
    raise ValueError("DAILY_DIGEST_TIME должен быть в формате HH:MM") from exc

if not (0 <= DAILY_DIGEST_HOUR <= 23 and 0 <= DAILY_DIGEST_MINUTE <= 59):
    raise ValueError("DAILY_DIGEST_TIME должен быть корректным временем в формате HH:MM")

# Настройки безопасности
MIN_DELAY_SECONDS = int(os.getenv("MIN_DELAY_SECONDS", "10"))
MAX_DELAY_SECONDS = int(os.getenv("MAX_DELAY_SECONDS", "30"))
MAX_STORIES_PER_CHECK = int(os.getenv("MAX_STORIES_PER_CHECK", "10"))

# VPN настройки
USE_VPN = os.getenv("USE_VPN", "false").lower() == "true"
VPN_PROTOCOL = os.getenv("VPN_PROTOCOL", "auto").strip().lower()
if VPN_PROTOCOL not in {"auto", "wireguard", "xray_vless"}:
    raise ValueError("VPN_PROTOCOL должен быть 'auto', 'wireguard' или 'xray_vless'")

VPN_CONFIG_PATH = os.getenv("VPN_CONFIG_PATH", "./config/wireguard.conf")
XRAY_CONFIG_PATH = os.getenv("XRAY_CONFIG_PATH", "/usr/local/etc/xray/config.json")

# Режимы работы
CATCH_UP_MODE = os.getenv("CATCH_UP_MODE", "true").lower() == "true"
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# Логирование
LOG_LEVEL = "DEBUG" if DEBUG_MODE else "INFO"
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# Лимиты для безопасности
MAX_ACTIONS_PER_SESSION = 50
MAX_SESSION_DURATION_HOURS = 2
MAX_RETRIES = 3
BACKOFF_FACTOR = 2

# Форматы файлов
ALLOWED_STORY_FORMATS = [".jpg", ".jpeg", ".png", ".mp4", ".mov"]
MAX_FILE_SIZE_MB = 50

# Сообщения для Telegram
MESSAGES = {
    "new_story": "🆕 Новая история от @{username}",
    "story_text": "📝 Текст: {text}",
    "story_link": "🔗 Ссылка: {link}",
    "error": "❌ Ошибка: {error}",
    "bot_started": "✅ Бот запущен и мониторит аккаунты: {accounts}",
    "bot_stopped": "⏹ Бот остановлен",
    "check_completed": "✔️ Проверка завершена. Новых историй: {count}",
    "vpn_error": "🔴 VPN не подключен!",
    "session_expired": "🔄 Сессия Instagram истекла, выполняется повторный вход...",
    "daily_digest_header": "📦 Ежедневная отправка stories за {timestamp}",
    "daily_digest_empty": "📭 На {timestamp} новых stories для отправки нет",
}
