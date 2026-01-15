import asyncio
import urllib.parse
from pathlib import Path
from typing import List, Optional

import subprocess
import os

import aiohttp
from dotenv import set_key
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response

from config import settings
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
    Только .xlsx файлы
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
    return Response(status_code=200)


@administration_router.get("/updateValidatorLinks")
async def update_validator_links(
    upload_all: Optional[bool] = Query(False, alias="uploadAll"),
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    upload_all = False -> убиваем процесс, в итоге fetch с сайта
    upload_all = True  -> удаляем файл и убиваем процесс —> отправляем все файлы в валидатор
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
    return Response(status_code=200)


@administration_router.get("/swapWeeks")
async def get_swap_weeks_state(
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    return {"swap_weeks": settings.swap_weeks}


@administration_router.post("/swapWeeks")
async def set_swap_weeks_state(
    swap_weeks: bool,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    set_key(".env", "SWAP_WEEKS", str(swap_weeks))  # str требуется библиотекой python-dotenv
    settings.swap_weeks = swap_weeks
    return {"swap_weeks": settings.swap_weeks}
