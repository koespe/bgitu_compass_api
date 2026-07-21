import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Body
from fastapi.responses import Response, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings, paths_config
from database.base import get_session_fastapi
from models.api import payloads
from models.database.models import Groups
from modules.excel_parser import process_schedule_file

administration_router = APIRouter(tags=["Administration"])
security = HTTPBearer()


def authenticate_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    password = credentials.credentials

    if not password == settings.admin_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


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


@administration_router.post("/removeGroups")
async def remove_groups(
    group_names: list[str],
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Авто-удаление групп по названию в валидаторе при появлении/исчезновении подгрупп, регистр неважен
    """
    normalized_names = [name.upper() for name in group_names]
    result = await session.execute(delete(Groups).where(func.upper(Groups.name).in_(normalized_names)))

    await session.commit()
    return {"deleted_count": result.rowcount}


@administration_router.post("/update")
async def upload_new_version(
    update_file: bytes = Body(media_type="application/octet-stream"),
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    Загрузить новую версию приложения
    """
    with open(paths_config.apk_file, "w+b") as file_in_dir:
        file_in_dir.write(update_file)
    return JSONResponse({"detail": "Файл успешно обновлен"})
