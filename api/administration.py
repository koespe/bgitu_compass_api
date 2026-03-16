import json
import urllib.parse
from pathlib import Path
from typing import List, Optional

import aiohttp
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings, paths_config
from database.base import get_session_fastapi
from models.api import payloads
from models.database.models import Groups
from modules.excel_parser import process_schedule_file
from modules.site_updates import check_site_files_updates

TELEGRAM_BOT_URL = (
    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage?"
    f"chat_id={settings.administration_chat_id}&"
    f"text="
)

administration_router = APIRouter(tags=["Administration"])
security = HTTPBearer()


def authenticate_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    password = credentials.credentials

    if not password == settings.admin_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


async def send_notify_telegram_message(message):
    async with aiohttp.ClientSession() as session:
        telegram_url = TELEGRAM_BOT_URL + urllib.parse.quote(message)
        try:
            await session.get(telegram_url)
        except Exception:
            pass


@administration_router.post(
    "/uploadNewSchedules",
    responses={
        400: {"description": "Принимаются только .xlsx файлы"},
    },
)
async def upload_new_schedules(
    files: List[UploadFile] = File(...),  # Multiple file uploads
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    Вызывается автоматически валидатором, но можно добавить файлы вручную

    Принимаются только .xlsx файлы
    """
    filenames = []
    for file in files:
        if Path(file.filename).suffix.lower() != ".xlsx":
            raise HTTPException(
                status_code=400,
                detail=f"Принимаются только .xlsx файлы. Некорректный файл: {file.filename}",
            )
    for file in files:
        filenames.append(file.filename)
        await process_schedule_file(file.file)

    await send_notify_telegram_message(message="Обновлены файлы:\n" + "\n".join(filenames))
    return Response()


@administration_router.get("/updateValidatorLinks")
async def update_validator_links(
    upload_all: Optional[bool] = Query(False, alias="uploadAll"),
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    Используется в валидаторе

    `upload_all` = `False` — принудительная проверка файлов на сайте

    `upload_all` = `True` — отправка всех файлов в валидатор с удалением хэшей
    """
    await check_site_files_updates(upload_all)
    return Response()


@administration_router.post("/teachersInfo")
async def post_teachers_info(
    data: payloads.TeachersInfo,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    При изменениях в валидаторе во вкладке "Преподаватели" сюда приходят обновленные данные по скрипту в Google Sheets
    """
    transformed_data = [
        {"name": teacher.name, "departments": [dept.strip() for dept in teacher.departments.split("+")]}
        for teacher in data.teachers
    ]

    with open(paths_config.teachers_info, "w", encoding="utf-8") as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=4)

    return Response()


@administration_router.delete(
    "/deleteGroup/{group_id}",
    responses={
        404: {"description": "Группа с указанным id не найдена"},
    },
)
async def delete_group(
    group_id: int,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
    session: AsyncSession = Depends(get_session_fastapi),
):
    result = await session.execute(delete(Groups).where(Groups.id == group_id))
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Группа с id={group_id} не найдена")
    await session.commit()
    return Response
