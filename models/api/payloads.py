from typing import List

from pydantic import BaseModel, HttpUrl, Field


class UploadUpdate(BaseModel):
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: str


class RemoteConfigUpdate(BaseModel):
    swapWeeks: bool
    lastResetTimestamp: str = Field(..., example="2023-01-01T12:00:00Z", description="ISO8601 UTC timestamp")
    versionCode: int
    downloadUrl: HttpUrl


class Teacher(BaseModel):
    name: str
    departments: str


class TeachersInfo(BaseModel):
    teachers: list[Teacher]
