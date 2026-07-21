from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer

from config import paths_config

general_router = APIRouter()
security = HTTPBearer()


CONTACTS = {
    "kirillPudov": {
        "vk": "https://vk.com/koespe",
        "tg": "https://t.me/koespe",
    },
    "eliseyVerevkin": {
        "vk": "https://vk.com/injent",
        "tg": "https://t.me/Injent",
    },
}


@general_router.get("/contacts/{person}/{service}", include_in_schema=False)
async def contact_redirect(person: str, service: str):
    person_data = CONTACTS.get(person)
    url = person_data.get(service)
    return RedirectResponse(url=url, status_code=301)


@general_router.get("/contacts/{person}/avatar.png", include_in_schema=False)
async def avatar(person: str):
    return FileResponse(f"public/{person}.png", media_type="image/png")


@general_router.get("/download")
async def download_apk():
    return FileResponse(
        paths_config.apk_file,
        media_type="application/vnd.android.package-archive",
        filename="bgitu_compass.apk",
    )


@general_router.get("/docs", response_class=HTMLResponse, include_in_schema=False)
async def plug():
    return (
        "<p>Если ты разработчик, потенциальный контрибьютор или просто "
        "очень настойчивый исследователь — добро пожаловать в DM, обсудим: "
        '<a href="https://t.me/koespe">https://t.me/koespe</a>'
    )
