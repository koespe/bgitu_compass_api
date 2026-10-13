import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials

from api.administration import authenticate_admin
from models.api import payloads, responses

profcom_router = APIRouter(tags=["Profcom"])

PROFCOM_SCHEDULES_PATH = Path("data/profcom_schedules.json")


@profcom_router.get(
    "/profcom/schedules",
    responses={
        200: {"model": responses.ProfcomFullResponse},
        404: {"description": "Файл profcom_schedules.json не найден"},
    },
)
async def get_profcom_schedules():
    if not PROFCOM_SCHEDULES_PATH.exists():
        raise HTTPException(status_code=404, detail="Файл profcom_schedules.json не найден")

    with open(PROFCOM_SCHEDULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@profcom_router.post("/profcom/schedules")
async def set_profcom_schedules(
    payload: payloads.ProfcomSchedulesPayload,
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    data = payload.model_dump(mode="json")
    with open(PROFCOM_SCHEDULES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return JSONResponse({"detail": "Success"})
