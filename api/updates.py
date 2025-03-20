import hashlib
import json

import aiohttp
from aiohttp.web_exceptions import HTTPError
from fastapi import APIRouter, HTTPException, Body, Response
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from fastapi.responses import JSONResponse, FileResponse

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
    with open(paths_config.apk_file, "w+b") as file_in_dir:
        file_in_dir.write(update_file)
    return JSONResponse({"detail": "Upload completed successfully"}, status_code=200)


@updates_router.post("/updateRemoteConfig")
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
    return Response(status_code=200)


@updates_router.get("/updateAvailability", responses={200: {"model": responses.UpdateAvailability}})
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
    return Response(status_code=200)


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
        raise HTTPException(status_code=404, detail=f"Changelog отсутствует для версии = {version}")
