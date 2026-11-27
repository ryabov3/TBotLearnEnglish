# 🎓 TBotLearnEnglish

Telegram-бот и **Telegram Mini App (React 18 + Vite + FastAPI)** для тренировки английского произношения в школе.

## 🧩 Распределение ответственности

- **Telegram-бот (`bot.py`, `handlers/student.py`):**
  - Регистрация (`/start` → выбор роли ученик/учитель → ввод имени и фамилии с валидацией `ValidNameFilter`).
  - Защита незарегистрированных пользователей (`RegistrationCheckMiddleware`) и логирование (`LoggingMiddleware`).
  - Запуск Mini App по кнопке **«🌐 Открыть Web App»** и кнопке меню Telegram (`MenuButtonWebApp`).
  - Приём голосовых и видео-ответов учеников по deep-link `/start task_<id>` и отправка медиа-ответа учителю для прослушивания по `/start review_<sub_id>`.
- **Telegram Mini App (`frontend/` + `webapp/`):**
  - Интерфейс на **React 18 + Vite + Framer Motion + Lucide React**, собранный в production-контейнер Nginx (проксирует `/api/*` на FastAPI).
  - **Ученик:** профиль, KPI стрика, смена имени, темы с прогресс-барами, быстрый переход к сдаче задания в боте, история оценок и комментариев.
  - **Учитель:** классы и группы, добавление/удаление учеников, создание и удаление тем с несколькими заданиями, проверка и оценка работ (1–5 + комментарий + кнопка прослушивания в боте), статистика по группам и ученикам.
  - **Админ и Основатель (`admin` / `founder`):** статистика системы, поиск и фильтрация пользователей, управление ролями (назначение/снятие администраторов только для `founder`), отвязка от групп, бан/разбан.

## 🗂 Архитектура проекта

```text
TBotLearnEnglish/
├── bot.py                      # Точка входа Telegram-бота
├── config/config.py            # Настройки из .env (MySQL, Redis, Proxy, Roles, WebApp)
├── database/                   # SQLAlchemy модели (models.py), движок (engine.py), Redis-кэш (cache.py)
├── handlers/student.py         # Регистрация, Web App кнопка, сдача и прослушивание медиа-ответов
├── keyboards/student.py        # Inline-клавиатуры бота
├── lexicon/lexicon.py          # Словарь фраз, команд и кнопок бота
├── middlewares/                # LoggingMiddleware и RegistrationCheckMiddleware
├── filters/                    # Фильтры ролей (role.py) и валидации имени (name.py)
├── states/states.py            # Состояния FSM (Registration, StudentTask)
├── migrations/                 # Миграции Alembic
├── webapp/                     # Модульный FastAPI API
│   ├── main.py                 # Сборка приложения, CORS, middlewares, routers
│   ├── dependencies/auth.py    # Проверка подписи Telegram initData (HMAC-SHA256)
│   ├── middlewares/logging.py  # Логирование HTTP-запросов и времени ответа
│   ├── schemas/                # Pydantic-схемы (profile.py, teacher.py, admin.py)
│   └── routers/                # Роутеры API (health, profile, student, teacher, admin)
├── frontend/                   # React 18 + Vite Mini App (multi-stage Dockerfile + Nginx)
│   ├── Dockerfile
│   ├── nginx.conf              # Раздача SPA и проксирование /api/ -> http://webapp:8000
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── api/client.js       # Fetch-клиент с заголовком X-Telegram-Init-Data
│       ├── components/         # Header, BottomNav, Modal, Toast, ProgressBar, EmptyState
│       ├── pages/              # Profile, Student*, Teacher*, Admin
│       └── styles/index.css    # Адаптивные стили под темы Telegram
├── Dockerfile                  # Сборка Python-сервисов (bot + webapp)
└── docker-compose.yml          # MySQL, Redis, FastAPI, React/Nginx, Bot, Adminer, Graylog
```

## 🐳 Запуск через Docker Compose

### 1. Создайте `.env` в корне проекта

```env
BOT_TOKEN=your_telegram_bot_token
BOT_USERNAME=your_bot_username

# Числовые Telegram ID через запятую (можно оставлять пустыми)
FOUNDERS_ID=123456789
ADMINS_ID=

# HTTPS-адрес вашего Mini App (указывайте на порт FRONTEND_PORT=3000 через Nginx/Caddy/cloudflared/ngrok)
WEBAPP_URL=https://your-https-domain.example.com
FRONTEND_PORT=3000
WEBAPP_PORT=8000
# Опционально для локального предпросмотра на http://localhost:3000 без Telegram (в продакшене пусто)
WEBAPP_DEV_USER_ID=

DB_USER=root
DB_PASSWORD=root
DB_HOST=db
DB_PORT=3306
DB_NAME=tbot_db

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_FSM_DB=1
REDIS_PASSWORD=
REDIS_TTL=600

OPENSEARCH_PASSWORD=StrongPassword123!

PROXY_LOGIN=
PROXY_PASSWORD=
PROXY_HOST=
PROXY_PORT=

GRAYLOG_HOST=graylog
GRAYLOG_PORT=12201
```

### 2. Запустите сервисы

```bash
docker compose up -d --build
```

| Сервис | Порт | Назначение |
| :--- | :---: | :--- |
| **frontend** | `3000` | React 18 + Vite Mini App (Nginx + прокси `/api` → `webapp:8000`) |
| **webapp** | `8000` | FastAPI REST API + проверка Telegram `initData` |
| **bot** | — | Telegram-бот (Aiogram 3 + Alembic миграции) |
| **db** | `3306` | MySQL 8 |
| **redis** | `6379` | Redis 7 (кэш MySQL + `RedisStorage` для FSM) |
| **adminer** | `8080` | Веб-интерфейс к MySQL |
| **graylog** | `9000` | Централизованные логи (с `mongodb` и `opensearch`) |
