# Instagram Story Monitor

Бот для мониторинга Instagram Stories и отправки уведомлений в Telegram.

## Возможности

- 📸 Автоматическая проверка новых Stories
- 💾 Скачивание фото и видео
- 📱 Уведомления в Telegram
- ⏰ Гибкое расписание проверок
- 🔒 Безопасная работа с имитацией поведения человека

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/YOUR_USERNAME/instagram-story-monitor.git
cd instagram-story-monitor
```

2. Создайте виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте переменные окружения:
```bash
cp .env.example .env
# Отредактируйте .env и добавьте свои данные
```

## Настройка

### Instagram
- `INSTAGRAM_USERNAME` - ваш логин Instagram
- `INSTAGRAM_PASSWORD` - ваш пароль

### Telegram
1. Создайте бота через @BotFather
2. Получите токен бота
3. Узнайте свой chat_id

### Отслеживаемые аккаунты
В файле `.env` укажите аккаунты через запятую:
```
TRACKED_ACCOUNTS=username1,username2
```

## Запуск

```bash
python run.py
```

Или используйте скрипт:
```bash
./scripts/run.sh
```

## Команды Telegram бота

- `/start` - Приветствие
- `/status` - Текущий статус
- `/stats` - Статистика
- `/users` - Список отслеживаемых аккаунтов
- `/add username` - Добавить аккаунт
- `/remove username` - Удалить аккаунт
- `/help` - Справка

## Структура проекта

```
├── src/
│   ├── instagram/     # Модули для работы с Instagram
│   ├── telegram/      # Telegram бот
│   ├── database/      # Работа с БД
│   └── utils/         # Утилиты
├── data/             # Данные приложения
│   ├── stories/      # Скачанные stories
│   └── bot.db        # База данных
├── logs/             # Логи
└── config/           # Конфигурация
```

## Безопасность

- Используйте отдельный Instagram аккаунт
- Не делайте слишком частые проверки
- При необходимости используйте VPN
- Храните `.env` файл в безопасности

## Лицензия

Private project. All rights reserved.