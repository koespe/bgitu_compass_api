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
async def upload_new_schedules(
    upload_all: Optional[bool] = Query(False, alias="uploadAll", description="Точное совпадение"),
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """

    uploadAll — принудительно отправляет в валидатор все файлы вместо автоматической отправки только измененных файлов"""
    try:
        pid = subprocess.check_output(f"pgrep -f site_updates.py", shell=True).decode().strip()

        if pid:
            pid = int(pid)
            try:
                # Отправляем сигнал SIGTERM (15) для завершения процесса
                os.kill(pid, 15)
                return Response(200)
            except OSError as e:
                try:
                    os.kill(pid, 9)
                    return Response(200)
                except OSError as e:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Ошибка при принудительном завершении процесса {pid}: {e}"
                    )
        else:
            raise HTTPException(
                status_code=400,
                detail="Не удалось найти процесс site_updates.py, возможно, он не запущен"
            )
    except subprocess.CalledProcessError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка при поиске процесса: {e}"
        )
