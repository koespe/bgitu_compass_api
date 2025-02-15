import datetime
import pathlib

from os import getenv
from types import SimpleNamespace

from dotenv import load_dotenv, find_dotenv

from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv(find_dotenv())

postgres_conn_str = getenv('POSTGRES_CONNECTION_STRING')
ADMIN_PASSWORD = getenv('ADMIN_PASSWORD')

engine = create_async_engine(postgres_conn_str)

HOSTNAME_PORT = 'http://localhost:8000'

# directories = SimpleNamespace() directories.apk
WORK_DIRECTORY = pathlib.Path('.')  # Последующее взаимодействие с файлами
EXCEL_DIRECTORY = pathlib.Path(WORK_DIRECTORY, 'data', 'saved_schedules')
APK_FILE = pathlib.Path(WORK_DIRECTORY, 'data', 'updates') / 'bgitu_compass.apk'
UPDATES_REMOTE_CONFIG = pathlib.Path(WORK_DIRECTORY, 'data', 'updates') / 'update_remote_config.json'
CHANGELOGS_DIR = pathlib.Path(WORK_DIRECTORY, 'data', 'changelogs')
SCHEDULE_UPLOAD_DATE = pathlib.Path(WORK_DIRECTORY, 'data', 'updates', 'scheduleUploadDate.json')

LOCALE_FILE = pathlib.Path(WORK_DIRECTORY, 'locals') / 'ru_RU.ini'

DEFAULT_TIMEZONE = datetime.timezone.utc

USER_DATA_VERSION = 1
