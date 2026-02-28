<table style="border: none; border-collapse: collapse;">
  <tr style="border: none;">
    <td style="border: none; padding: 0;">
      <img src="https://bgitu-compass.ru/assets/compass_logo_big_old.png" width="100" alt="BGITU Compass Logo">
    </td>
    <td style="border: none; padding: 0 10px;">
      <h1>БГИТУ Компас (Backend API)</h1>
      <p>Backend для мобильного приложения и бота «БГИТУ Компас». Предоставляет доступ к расписанию занятий, информации о преподавателях ФГБОУ ВО «БГИТУ»</p>
    </td>
  </tr>
</table>

## Требования

- **Python 3.9+**
- PostgreSQL

## Технологии

- **FastAPI** — веб-фреймворк
- **SQLAlchemy (async)** — ORM
- **PostgreSQL + asyncpg** — база данных
- **openpyxl** — парсинг Excel

## Установка

1. Клонировать репозиторий

2. Установить зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Создать `.env` файл на основе `.env.example`

## Запуск

```bash
python app.py
```

Документация API доступна по адресу: http://localhost:8000/documentation

## Структура проекта

```
bgitu_api/
├── api/           # FastAPI роутеры
├── database/      # Работа с БД
├── models/        # Pydantic и SQLAlchemy модели
├── modules/       # Парсеры Excel и сайта
├── data/          # JSON-конфиги и файлы обновленй
├── scripts/       # Скрипты для деплоя
├── config.py      # Конфигурация
└── app.py         # Точка входа
```
