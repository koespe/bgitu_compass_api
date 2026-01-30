from fastapi import APIRouter
from fastapi.security import HTTPBearer
from fastapi.responses import HTMLResponse

general_router = APIRouter()
security = HTTPBearer()


@general_router.get("/docs", response_class=HTMLResponse, include_in_schema=False)
@general_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def plug():
    return (
        "Очень интересно, что ты стал исследовать API проекта. "
        "Если хочешь получить доступ к документации или улучшить проект, пиши —> "
        '<a href="https://t.me/koespe">https://t.me/koespe</a>'
    )
