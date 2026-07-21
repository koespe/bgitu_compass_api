import hashlib
import json
from pathlib import Path

import aiohttp
from aiohttp.web_exceptions import HTTPError
from fastapi import APIRouter, HTTPException, Body, Response
from fastapi import Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.administration import authenticate_admin
from config import paths_config
from models.api import payloads, responses

updates_router = APIRouter(tags=["App updates"])
security = HTTPBearer()


@updates_router.post("/update")
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


@updates_router.post("/updateRemoteConfig", deprecated=True)
async def upload_new_version(
    payload: payloads.UploadUpdate,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    Оставлено для обратной совместимости

    Обновляет файл update_remote_config.json — НЕ ПУТАТЬ С remote_config.json
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(payload.downloadUrl) as response:
            try:
                response.raise_for_status()
                update_file_bytes = await response.read()
            except HTTPError:
                raise HTTPException(detail="Невозможно скачать файл", status_code=400)

    update_file_size = len(update_file_bytes)

    hasher = hashlib.sha256()
    hasher.update(update_file_bytes)
    update_file_checksum = hasher.hexdigest()

    remote_config_data = payload.model_dump()
    remote_config_data["size"] = update_file_size
    remote_config_data["checksum"] = update_file_checksum

    with open(paths_config.updates_remote_config, "w") as f:
        json.dump(remote_config_data, f)

    with open(paths_config.apk_file, "w+b") as file_in_dir:
        file_in_dir.write(update_file_bytes)
    return Response()


@updates_router.get("/updateAvailability", deprecated=True, responses={200: {"model": responses.UpdateAvailability}})
async def update_availability():
    """
    Старый роут для обратной совместимости
    """
    with open(paths_config.updates_remote_config, "r") as f:
        data = json.load(f)
    return data


@updates_router.get("/changelog", deprecated=True)
async def get_changelog(version: int):
    """
    Старый роут для обратной совместимости
    """
    path = paths_config.changelogs / f"{version}.md"
    if path.exists():
        return FileResponse(
            path=paths_config.changelogs / f"{version}.md",
            filename=f"{version}.md",
            media_type="text/markdown",
        )
    else:
        raise HTTPException(status_code=404, detail=f"Changelog отсутствует для версии {version}")


@updates_router.get(
    "/remoteConfig",
    responses={
        200: {"model": responses.RemoteConfig},
        404: {"description": "Файл remote_config.json не найден. Необходимо создать через POST запрос"},
    },
)
async def get_remote_config():
    """
    - `termStartDate` - опорная дата для расчета четности недели (очередность first_week/second_week).
    Нужна, чтобы вручную сдвигать цикл недель, если учебный отдел меняет график посреди семестра
        ```python
        week_num = ((current_date - term_start_date).days // 7) + 1
        return "second_week" if week_num % 2 == 0 else "first_week"
        ```
    - `lastResetTimestamp` - метка времени последнего сброса данных групп (truncate table groups)
    - `teacherSearchWarningDateRanges` - список диапазонов дат в формате [["MM-DD", "MM-DD"], ...] для предупреждений
    о возможных ошибках при поиске преподавателей ввиду сессии
    - `versionCode` - номер актуальной версии приложения (для проверки обновлений)
    - `downloadUrl` - ссылка на скачивание актуального APK-файла
    """
    config_path = Path(paths_config.remote_config)
    if not config_path.exists():
        raise HTTPException(status_code=404, detail="Для начала создайте файл remote_config.json через POST запрос")

    with open(config_path, "r") as f:
        return json.load(f)


@updates_router.post("/remoteConfig")
async def update_remote_config(
    payload: payloads.RemoteConfigUpdate,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    config_path = Path(paths_config.remote_config)
    config_data = payload.model_dump(mode="json")

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)

    return JSONResponse({"detail": "Success"})
