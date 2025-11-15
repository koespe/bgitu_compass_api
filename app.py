import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from icecream import ic

from api.administration import administration_router
from api.general import general_router
from api.schedules import schedules_router
from api.updates import updates_router
from config import settings

from database.base import db_init


async def lifespan():
    await db_init()

    # Отключаем логирование на production
    if "prod" in settings.admin_password:
        ic.disable()


app = FastAPI(
    title="BGITU Compass API",
    version="2.0 (using Validator`s data)",
    on_startup=[lifespan],
    docs_url=None,
    redoc_url=None,
    debug=False
)


app.include_router(general_router)
app.include_router(administration_router)
app.include_router(updates_router)
app.include_router(schedules_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
