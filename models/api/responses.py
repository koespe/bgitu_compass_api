from datetime import date, time, datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, Field


class UpdateAvailability(BaseModel):
    size: int
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: HttpUrl


class TeacherLocationPerLesson(BaseModel):
    subjectName: str
    classroom: str
    building: str
    isLecture: bool
    lessonDate: date
    startAt: time = Field(..., example="12:20:00")
    endAt: time = Field(..., example="14:20:00")
    weekday: int


class TeacherLocations(BaseModel):
    teacher: str
    data: List[TeacherLocationPerLesson]


class Groups(BaseModel):
    id: int
    name: str


class GroupsInfo(BaseModel):
    id: int
    name: str
    scheduleUpdateDate: Optional[datetime] = None


class ScheduleVersion(BaseModel):
    scheduleVersion: int
    forceUpdateVersion: int


class RemoteConfig(BaseModel):
    swapWeeks: bool
    lastResetTimestamp: str = Field(..., example="2023-01-01T12:00:00Z", description="ISO8601 UTC timestamp")
    versionCode: int
    downloadUrl: HttpUrl


class Teacher(BaseModel):
    name: str
    departments: list[str]
