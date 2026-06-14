# Instagram Story Monitor

Скрипт отслеживает Instagram Stories, скачивает новые медиа локально и отправляет их в Telegram. Поддерживает два режима доставки:

- `immediate`: отправлять сторис сразу после проверки.
- `daily_digest`: копить новые сторис и отгружать их в Telegram один раз в день в заданное время.

Также добавлена поддержка `Xray + VLESS`: приложение умеет читать `/usr/local/etc/xray/config.json`, находить локальный `socks` или `http` inbound и использовать его как proxy для `instagrapi`.

## Что делают интервальные настройки

- `CHECK_INTERVAL_HOURS=4`
  Это базовый интервал проверки Instagram. Значение `4` означает: бот делает новый обход аккаунтов примерно раз в 4 часа.

- `INTERVAL_RANDOMNESS_MINUTES=30`
  Это случайное отклонение вокруг базового интервала. Значение `30` означает: к каждой проверке добавляется jitter до `±30` минут, чтобы бот не ходил в Instagram строго по часам.

Пример:
при `CHECK_INTERVAL_HOURS=4` и `INTERVAL_RANDOMNESS_MINUTES=30` фактический интервал будет около `3ч 30м` - `4ч 30м`.

## Установка на Debian/Ubuntu

### 1. Установить системные зависимости

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

Если планируется WireGuard:

```bash
sudo apt install -y wireguard-tools
```

Если планируется Xray:

```bash
sudo systemctl status xray
```

Ожидается, что `xray` уже установлен и использует конфиг `/usr/local/etc/xray/config.json`.

### 2. Клонировать репозиторий

```bash
git clone https://github.com/Danchik757/instagram-story-monitor.git
cd instagram-story-monitor
```

### 3. Создать виртуальное окружение

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Настроить `.env`

```bash
cp .env.example .env
```

Минимальный пример:

```env
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password

TELEGRAM_BOT_TOKEN=123456:bot_token
TELEGRAM_CHAT_ID=123456789

TRACKED_ACCOUNTS=friend1,friend2

CHECK_INTERVAL_HOURS=4
INTERVAL_RANDOMNESS_MINUTES=30

TELEGRAM_DELIVERY_MODE=daily_digest
DAILY_DIGEST_TIME=21:00

USE_VPN=true
VPN_PROTOCOL=xray_vless
XRAY_CONFIG_PATH=/usr/local/etc/xray/config.json
```

## Настройка Telegram-отправки

### Отправка сразу после проверки

```env
TELEGRAM_DELIVERY_MODE=immediate
```

В этом режиме новые сторис уходят в Telegram сразу после очередной проверки.

### Отправка раз в день

```env
TELEGRAM_DELIVERY_MODE=daily_digest
DAILY_DIGEST_TIME=21:00
```

В этом режиме бот:

- продолжает проверять Instagram по `CHECK_INTERVAL_HOURS`;
- скачивает найденные сторис в локальную папку;
- не отправляет их сразу;
- в `21:00` отправляет накопленные сторис в Telegram одной дневной выгрузкой.

Формат `DAILY_DIGEST_TIME` строго `HH:MM`.

## Настройка VPN / proxy

### WireGuard

```env
USE_VPN=true
VPN_PROTOCOL=wireguard
VPN_CONFIG_PATH=./config/wireguard.conf
```

Приложение проверяет, что интерфейс WireGuard активен, и при необходимости может использовать `wg-quick`.

### Xray + VLESS

```env
USE_VPN=true
VPN_PROTOCOL=xray_vless
XRAY_CONFIG_PATH=/usr/local/etc/xray/config.json
```

Как это работает:

- приложение читает `config.json`;
- ищет локальный inbound с протоколом `socks` или `http`;
- берет `host:port` этого inbound;
- передает его в `instagrapi` как proxy;
- проверяет, что процесс `xray` активен.

Важно:
само приложение не поднимает `xray`. Сервис должен быть запущен заранее, например через `systemd`.

## Запуск

После активации окружения:

```bash
python run.py
```

Альтернатива:

```bash
python main.py
```

## Запуск как `systemd` service на Debian/Ubuntu

Пример файла `/etc/systemd/system/instagram-story-monitor.service`:

```ini
[Unit]
Description=Instagram Story Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/opt/instagram-story-monitor
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/instagram-story-monitor/.venv/bin/python /opt/instagram-story-monitor/run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable instagram-story-monitor
sudo systemctl start instagram-story-monitor
sudo systemctl status instagram-story-monitor
```

Если используете `xray`, имеет смысл добавить зависимость:

```ini
After=network-online.target xray.service
Wants=network-online.target xray.service
```

## Команды Telegram-бота

- `/start`
- `/status`
- `/stats`
- `/users`
- `/add username`
- `/remove username`
- `/help`

## Структура данных

- `data/stories/`: скачанные stories
- `data/bot.db`: SQLite база
- `data/sessions/`: сохраненные сессии Instagram
- `logs/`: ежедневные логи

## Ограничения

- Для `Xray/VLESS` в `config.json` должен существовать локальный `socks` или `http` inbound, иначе приложению нечего будет использовать как proxy.
- Если `TELEGRAM_DELIVERY_MODE=daily_digest`, новые сторис не отправляются сразу, а ждут окна ежедневной выгрузки.
- Двухфакторная аутентификация Instagram может мешать автоматическому входу через `instagrapi`.
