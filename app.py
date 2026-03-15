from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.administration import administration_router
from api.checks import checks_router
from api.general import general_router
from api.schedules import schedules_router
from api.teachers import teachers_router
from api.updates import updates_router
from database.base import db_init
from modules.annual_data_reset import annual_data_reset
from modules.site_updates import check_site_files_updates
from modules.term_start_date_scraper import check_site_variable_updates

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db_init()

    scheduler.add_job(check_site_files_updates, "interval", minutes=5, next_run_time=datetime.now())
    scheduler.add_job(check_site_variable_updates, "interval", minutes=60, next_run_time=datetime.now())
    scheduler.add_job(annual_data_reset, "cron", month=7, day=15, hour=0, minute=0, second=0)

    scheduler.start()

    yield

    scheduler.shutdown(wait=True)


app = FastAPI(
    title="BGITU Compass API",
    version="using Validator`s data",
    lifespan=lifespan,
    docs_url="/documentation",
    redoc_url=None,
    debug=False,
)


app.include_router(general_router)
app.include_router(schedules_router)
app.include_router(teachers_router)
app.include_router(administration_router)
app.include_router(updates_router)
app.include_router(checks_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
