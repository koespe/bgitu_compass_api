from datetime import date, time
from typing import List

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


class ScheduleVersion(BaseModel):
    scheduleVersion: int
    forceUpdateVersion: int


class RemoteConfig(BaseModel):
    swapWeeks: bool
    lastResetTimestamp: int
    versionCode: int
    downloadUrl: HttpUrl
