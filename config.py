import pathlib

from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import create_async_engine


class PathsConfig(BaseSettings):
    work_directory: pathlib.Path = pathlib.Path(".")
    apk_file: pathlib.Path = work_directory / "data" / "updates" / "bgitu_compass.apk"
    updates_remote_config: pathlib.Path = work_directory / "data" / "updates" / "update_remote_config.json"
    remote_config: pathlib.Path = work_directory / "data" / "remote_config.json"
    changelogs: pathlib.Path = work_directory / "data" / "changelogs"
    schedule_hashes: pathlib.Path = work_directory / "data" / "schedule_hashes.json"
    teachers_info: pathlib.Path = work_directory / "data" / "teachers_info.json"


class Settings(BaseSettings):
    user_data_version: int  # Индикатор для приложения о смене учебного года (для обратной совместимости версий)
    swap_weeks: bool  # first и second week могут поменять местами

    admin_password: str
    postgres_password: str
    postgres_connection_string: str

    @property
    def engine(self):
        return create_async_engine(self.postgres_connection_string)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


paths_config = PathsConfig()
settings = Settings()
