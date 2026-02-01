import hashlib
import json
from pathlib import Path

import aiohttp
from aiohttp.web_exceptions import HTTPError
from dotenv import set_key
from fastapi import APIRouter, HTTPException, Body, Response
from fastapi import Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from api.administration import authenticate_admin
from config import paths_config
from config import settings
from models.api import payloads, responses

updates_router = APIRouter(tags=["App updates"])
security = HTTPBearer()


@updates_router.post("/update")
async def upload_new_version(
    update_file: bytes = Body(media_type="application/octet-stream"),
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    with open(paths_config.apk_file, "w+b") as file_in_dir:
        file_in_dir.write(update_file)
    return JSONResponse({"detail": "Файл успешно обновлен"})


@updates_router.post("/updateRemoteConfig", deprecated=True)
async def upload_new_version(
    payload: payloads.UploadUpdate,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
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
    with open(paths_config.updates_remote_config, "r") as f:
        data = json.load(f)
    return data


@updates_router.post("/createChangelog")
def use_body(
    version: int,
    changelog: bytes = Body(media_type="application/octet-stream"),
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    with open(paths_config.changelogs / f"{version}.md", "wb") as changelog_file:
        changelog_file.write(changelog)
    return Response()


@updates_router.get("/changelog")
async def get_changelog(version: int):
    path = paths_config.changelogs / f"{version}.md"
    if path.exists():
        return FileResponse(
            path=paths_config.changelogs / f"{version}.md",
            filename=f"{version}.md",
            media_type="text/markdown",
        )
    else:
        raise HTTPException(status_code=404, detail=f"Changelog отсутствует для версии {version}")


@updates_router.get("/remoteConfig", responses={200: {"model": responses.RemoteConfig}})
async def get_remote_config():
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

    # Обновляем swapWeeks в .env файле для быстрого доступа к этой переменной
    set_key(".env", "SWAP_WEEKS", str(payload.swapWeeks))
    settings.swap_weeks = payload.swapWeeks

    with open(config_path, "w") as f:
        json.dump(config_data, f, indent=2)

    return JSONResponse({"detail": "Success"})
