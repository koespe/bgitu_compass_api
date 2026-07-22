<div style="display: flex; align-items: center; gap: 20px;">
  <img src="https://bgitu-compass.ru/assets/compass_logo_big_old.png" width="100" alt="BGITU Compass Logo">
  <div>
    <h1><a href="https://bgitu-compass.ru">БГИТУ Компас</a> (Backend API)</h1>
    <p>Backend для мобильного приложения и бота. Предоставляет доступ к расписанию занятий, информации о преподавателях ФГБОУ ВО "Брянский государственный инженерно-технологический университет".</p>
    <p>🤖 <a href="https://t.me/bgitu_compass_bot">Telegram-бот</a> | 🌐 <a href="https://bgitu-compass.ru">Приложение для Android</a></p>
  </div>
</div>

## Требования

- **Python 3.9+**
- PostgreSQL

## Технологии

- **FastAPI** — веб-фреймворк
- **SQLAlchemy (async)** — ORM
- **PostgreSQL + asyncpg** — база данных
- **openpyxl** — парсинг Excel

## Установка (локально)

1. Клонировать репозиторий

2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Создать `.env` файл на основе `.env.example`

## Запуск (локально)

```bash
python app.py
```

Документация API доступна по адресу: http://localhost:8000/documentation

## Docker

### Требования

- Docker
- Docker Compose

### Запуск

1. Создать `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Запустить:
   ```bash
   docker compose up -d
   ```

Docker-compose автоматически переопределяет `POSTGRES_CONNECTION_STRING` для подключения к postgres внутри docker-сети —
менять `localhost` на `postgres` в `.env` не нужно.

Порт API задаётся переменной `API_EX_PORT` в `.env` (по умолчанию 8000). Для nginx:

```
API_EX_PORT=8000
```

Посмотреть логи:

   ```bash
   docker compose logs -f
   ```

Остановить:

   ```bash
   docker compose down
   ```

### Важно

- SSL не встроен, но мобильное приложение будет требовать HTTPS
- База данных сохраняется в named volume `pgdata`, не теряется при `down`

## Структура проекта

```
bgitu_api/
├── api/           # FastAPI роутеры
├── database/      # Работа с БД
├── models/        # Pydantic и SQLAlchemy модели
├── modules/       # Парсеры Excel и сайта
├── data/          # JSON-конфиги и файлы обновленй
├── public/        # Статика SPA
├── Dockerfile     # Сборка контейнера FastAPI
├── docker-compose.yml
├── .dockerignore  # Исключения из Docker-образа
├── config.py      # Конфигурация
└── app.py         # Точка входа
```
