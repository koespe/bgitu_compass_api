from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer

general_router = APIRouter()
security = HTTPBearer()


@general_router.get("/docs", response_class=HTMLResponse, include_in_schema=False)
@general_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def plug():
    return (
        "<p>Если ты разработчик, потенциальный контрибьютор или просто "
        "очень настойчивый исследователь — добро пожаловать в DM, обсудим: "
        '<a href="https://t.me/koespe">https://t.me/koespe</a>'
    )
