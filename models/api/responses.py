from datetime import date, time
from typing import Optional, List

from pydantic import BaseModel, HttpUrl, Field


class Credentials(BaseModel):
    accessToken: str
    refreshToken: str
    expirationDate: str


class RegisterGuest(BaseModel):
    userId: int
    groupId: int
    groupName: str
    credentials: Credentials


class RegisterEosUser(BaseModel):
    userId: int
    eosUserId: int
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    credentials: Credentials


class AccountData(BaseModel):
    userId: int
    eosUserId: Optional[int] = None
    groupId: Optional[int] = None
    groupName: Optional[str] = None
    fullName: Optional[str] = None
    avatarUrl: Optional[HttpUrl] = None
    role: str
    permissions: list
    additionalData: dict


class UpdateUUID(BaseModel):
    user_id: int


class UpdateAvailability(BaseModel):
    size: int
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: HttpUrl


class TeacherSearchQuery(BaseModel):
    data: List[str]


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


class Subjects(BaseModel):
    id: int
    name: str


class Groups(Subjects):  # Одинаковый response
    pass


class Lessons(BaseModel):
    id: int
    subjectId: int
    lessonDate: date
    weekday: int
    startAt: time = Field(..., example="12:20:00")
    endAt: time = Field(..., example="12:20:00")
    building: str
    classroom: str
    isLecture: bool
    teacher: str


class ScheduleVersion(BaseModel):
    scheduleVersion: int
    forceUpdateVersion: int


class GetDataByTGID(BaseModel):
    group_id: int
    group_name: str
