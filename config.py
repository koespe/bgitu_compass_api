import pathlib

from pydantic_settings import BaseSettings

from sqlalchemy.ext.asyncio import create_async_engine


class PathsConfig(BaseSettings):
    work_directory: pathlib.Path = pathlib.Path(".")
    apk_file: pathlib.Path = work_directory / "data" / "updates" / "bgitu_compass.apk"
    updates_remote_config: pathlib.Path = work_directory / "data" / "updates" / "update_remote_config.json"
    changelogs: pathlib.Path = work_directory / "data" / "changelogs"
    schedule_hashes: pathlib.Path = work_directory / "data" / "schedule_hashes.json"

    schedule_upload_date: pathlib.Path = work_directory / "data" / "updates" / "scheduleUploadDate.json"


class Settings(BaseSettings):
    # Настройки для чекера обновлений и уведомлений о новых файлах
    telegram_bot_token: str
    admin_tg_id: int
    validator_url: str

    admin_password: str
    postgres_connection_string: str

    @property
    def engine(self):
        return create_async_engine(self.postgres_connection_string)

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


paths_config = PathsConfig()
settings = Settings()
