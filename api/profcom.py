import aiohttp
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from config import settings

profcom_router = APIRouter(tags=["Profcom"])

PROFCOM_CONFIG_URL = "https://validator.bgitu.ru/api/schedules/config"


@profcom_router.get(
    "/profkom/config",
    responses={
        502: {"description": "Не удалось получить конфигурацию с validator.bgitu.ru"},
    },
)
async def get_profkom_config():
    headers = {"X-Api-Key": settings.admin_password}

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            async with session.get(PROFCOM_CONFIG_URL, headers=headers) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
    except (aiohttp.ClientError, ValueError):
        raise HTTPException(
            status_code=502,
            detail="Не удалось получить конфигурацию с validator.bgitu.ru",
        )

    return JSONResponse(data)
