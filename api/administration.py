import asyncio
import json
import os
import subprocess
import urllib.parse
from pathlib import Path
from typing import List, Optional

import aiohttp
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.responses import Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings, paths_config
from database.base import get_session_fastapi
from models.api import payloads, responses
from models.database.models import Groups
from modules.excel_parser import process_schedule_file

TELEGRAM_BOT_URL = (
    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage?chat_id={settings.admin_tg_id}&text="
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


@administration_router.post("/uploadNewSchedules")
async def upload_new_schedules(
    files: List[UploadFile] = File(...),  # Multiple file uploads
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    Вызывается автоматически валидатором, но можно добавить файлы вручную.

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
    `upload_all` = `False` -> убиваем процесс, в итоге fetch с сайта

    `upload_all` = `True` -> удаляем файл и убиваем процесс —> отправляем все файлы в валидатор
    """
    if upload_all:
        os.remove("data/schedule_hashes.json")

    try:
        pids = subprocess.check_output("pgrep -f site_updates.py", shell=True).decode().strip().split("\n")
        if pids and pids != [""]:
            killed_any = False
            for pid_str in pids:
                try:
                    pid = int(pid_str)
                    os.kill(pid, 15)  # SIGTERM
                    killed_any = True
                except OSError:
                    # Если не удалось отправить SIGTERM, убиваем силой
                    try:
                        pid = int(pid_str)
                        os.kill(pid, 9)
                        killed_any = True
                    except Exception:
                        pass
            if not killed_any:
                raise HTTPException(400, detail="Процесс site_updates.py не найден")
        else:
            raise HTTPException(400, detail="Процесс site_updates.py не найден")

    except subprocess.CalledProcessError as e:
        raise HTTPException(400, detail=f"Ошибка при поиске процесса: {e}")

    await asyncio.sleep(20)  # Для лучшего понимания задержки на сайте валидатора
    return Response()


@administration_router.post("/teachersInfo")
async def post_teachers_info(
    data: payloads.TeachersInfo,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    При изменениях в валидаторе во вкладке "Преподаватели" сюда приходят обновленные данные из Google Sheets
    """
    transformed_data = [
        {"name": teacher.name, "departments": [dept.strip() for dept in teacher.departments.split("+")]}
        for teacher in data.teachers
    ]

    with open(paths_config.teachers_info, "w", encoding="utf-8") as f:
        json.dump(transformed_data, f, ensure_ascii=False, indent=4)

    return Response()


@administration_router.get("/groupsInfo", response_model=List[responses.GroupsInfo])
async def get_groups_info(
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Используется в валидаторе для администрирования групп
    """
    result = await session.execute(select(Groups.id, Groups.name, Groups.scheduleUpdateDate))
    groups_data = result.all()

    groups_info = []
    for group in groups_data:
        groups_info.append({"id": group.id, "name": group.name, "scheduleUpdateDate": group.scheduleUpdateDate})

    return groups_info


@administration_router.delete("/deleteGroup/{group_id}")
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


@administration_router.get("/checkMissingTeachers")
async def check_missing_teachers(
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Временный route через ChatGPT для проверки до сентября 2026

    Проверяет все группы в rawSchedule и проверяет наличие преподавателей в списке fullTeacherName
    Возвращает список групп с отсутствующими преподавателями
    """
    # Получаем список всех преподавателей из файла teachers_info
    teachers_info_path = Path(paths_config.teachers_info)
    if not teachers_info_path.exists():
        raise HTTPException(status_code=404, detail="Файл teachers_info не найден")

    with open(teachers_info_path, "r", encoding="utf-8") as f:
        teachers_data = json.load(f)

    # Создаем множество коротких имен преподавателей для быстрого поиска
    teacher_short_names = set()
    for teacher in teachers_data:
        full_name = teacher.get("name", "").strip()
        if full_name:
            # Преобразуем полное имя в короткое (например, "Иванов Иван Иванович" -> "Иванов И.И.")
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                surname = name_parts[0]
                initials = "".join(f"{p[0]}." for p in name_parts[1:3])
                short_name = f"{surname} {initials}"
                teacher_short_names.add(short_name)

    # Получаем все группы с их расписаниями
    result = await session.execute(select(Groups.name, Groups.rawSchedule))
    groups_data = result.all()

    # Проверяем каждую группу на наличие преподавателей, которых нет в списке
    missing_teachers_result = []

    for group in groups_data:
        group_name = group.name
        raw_schedule = group.rawSchedule

        if not raw_schedule:
            continue

        missing_teachers_in_group = set()

        # Проходим по всем неделям и дням в расписании
        for week_name, week_schedule in raw_schedule.items():
            for day_name, day_lessons in week_schedule.items():
                for lesson in day_lessons:
                    teacher_name = lesson.get("teacher")
                    if teacher_name and teacher_name not in teacher_short_names:
                        missing_teachers_in_group.add(teacher_name)

        # Если есть отсутствующие преподаватели в этой группе, добавляем в результат
        if missing_teachers_in_group:
            missing_teachers_result.append({"group": group_name, "unknownTeacher": list(missing_teachers_in_group)})

    return missing_teachers_result
