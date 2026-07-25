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

### Сервисы

| Сервис         | Описание                    | Порт                   |
|----------------|-----------------------------|------------------------|
| `fastapi`      | Backend API                 | `${API_EX_PORT}`       |
| `compassadmin` | Админ-панель Compass (Ktor) | `${VALIDATOR_EX_PORT}` |
| `watchtower`   | Автообновление compassadmin | —                      |
| `postgres`     | PostgreSQL                  | —                      |

### Первый запуск

1. Создать `.env` на основе `.env.example`:
   ```bash
   cp .env.example .env
   ```

2. Создать `.env.compass-admin` на основе `.env.compass-admin.example`:
   ```bash
   cp .env.compass-admin.example .env.compass-admin
   ```
   Заполнить реальными значениями. **Если не знаете credentials** — обратитесь к [@Injent](https://t.me/Injent).

3. Положить `credentials.json` от Google API в папку:
   ```
   compass-admin-config/google/credentials.json
   ```
   Если файла нет — обратитесь к [@Injent](https://t.me/Injent).

4. Запустить:
   ```bash
   docker compose up -d
   ```

### Обновления

- **compassadmin** обновляется автоматически через watchtower (каждые 5 минут проверяет ghcr.io на наличие нового
  образа)
- **fastapi** обновляется через пересборку:
  ```bash
  docker compose build fastapi && docker compose up -d fastapi
  ```

### Полезные команды

Посмотреть логи:

```bash
docker compose logs -f
```

Логи только compassadmin:

```bash
docker compose logs -f compassadmin
```

Остановить:

```bash
docker compose down
```

### Важно

- SSL не встроен, но мобильное приложение будет требовать HTTPS
- База данных сохраняется в named volume `pgdata`, не теряется при `down`
- Данные compassadmin (SQLite, токены) хранятся в `compass-admin-config/data/` и `compass-admin-config/tokens/`
- Файлы `.env`, `.env.compass-admin`, `compass-admin-config/google/`, `compass-admin-config/tokens/`,
  `compass-admin-config/data/` не попадают в git

## Структура проекта

```
bgitu_api/
├── api/                              # FastAPI роутеры
├── database/                         # Работа с БД
├── models/                           # Pydantic и SQLAlchemy модели
├── modules/                          # Парсеры Excel и сайта
├── data/                             # JSON-конфиги и файлы обновленй
├── public/                           # Статика SPA
├── compass-admin-config/             # Конфиг compassadmin (монтируется в контейнер)
│   ├── application.yaml              # Шаблон конфига (с ${VAR} плейсхолдерами)
│   ├── google/credentials.json       # Google API ключи (в .gitignore)
│   ├── tokens/                       # Google OAuth токены (в .gitignore)
│   └── data/                         # SQLite база compassadmin (в .gitignore)
├── Dockerfile                        # Сборка контейнера FastAPI
├── docker-compose.yml
├── .env.example                      # Шаблон для backend
├── .env.compass-admin.example        # Шаблон для compassadmin
├── .dockerignore
├── config.py                         # Конфигурация
└── app.py                            # Точка входа
```
