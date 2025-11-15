from pathlib import Path
from typing import List, Optional

import subprocess
import os

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response

from config import settings
from modules.excel_parser import process_schedule_file


administration_router = APIRouter(tags=["Administration"])
security = HTTPBearer()


def authenticate_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    password = credentials.credentials

    if not password == settings.admin_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@administration_router.post("/uploadNewSchedules")
async def upload_new_schedules(
    files: List[UploadFile] = File(...),  # Multiple file uploads
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    Только .xlsx файлы
    """
    for file in files:
        if Path(file.filename).suffix.lower() != ".xlsx":
            raise HTTPException(
                status_code=400,
                detail=f"Принимаются только .xlsx файлы. Некорректный файл: {file.filename}",
            )
    for file in files:
        await process_schedule_file(file.file)

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
