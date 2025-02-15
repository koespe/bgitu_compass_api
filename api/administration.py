from fastapi import APIRouter, HTTPException, Depends, Body, Form, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse

from config import ADMIN_PASSWORD
from models.api.payloads import DatabaseAction

from modules.excel_parser.timetable_excel import initialize_excel_schedules

administration_router = APIRouter(tags=["Администрирование"])
security = HTTPBearer()


def authenticate_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    password = credentials.credentials

    if not password == ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


@administration_router.post("/databaseActions")
async def database_actions(
    action: DatabaseAction = Body(),
    auth: HTTPAuthorizationCredentials = Depends(authenticate_admin),
):
    """
    Actions: full_reset | reset_schedules(truncate Lessons) | reset_schedules_and_subjects | just_update_raw_schedules
    """
    action = action.action
    if action == "full_reset":
        await initialize_excel_schedules(full_reset=True)
    elif action == "reset_schedules":
        await initialize_excel_schedules(reset_schedules=True)
        return "reset"
    elif action == "reset_schedules_and_subjects":
        await initialize_excel_schedules(reset_schedules_and_subjects=True)
    elif action == "just_update_raw_schedules":
        await initialize_excel_schedules()
    else:
        return JSONResponse({"msg": "No action provided"})
    return "Success"
