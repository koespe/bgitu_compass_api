import datetime
from datetime import date, time
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
    scheduleUpdateDate: Optional[int] = None


class ScheduleVersion(BaseModel):
    scheduleVersion: int
    forceUpdateVersion: int


class RemoteConfig(BaseModel):
    termStartDate: datetime.date
    swapWeeks: bool
    lastResetTimestamp: str = Field(..., example="2023-01-01T12:00:00Z", description="ISO8601 UTC timestamp")
    versionCode: int
    downloadUrl: HttpUrl
    vkLinkSupport: Optional[HttpUrl] = None
    maxLinkSupport: Optional[HttpUrl] = None
    telegramLinkSupport: Optional[HttpUrl] = None
    teacherSearchWarningDateRanges: Optional[List[List[str]]] = Field(
        None, example=[["12-08", "02-07"], ["05-11", "07-15"]]
    )


class Teacher(BaseModel):
    name: str = Field(..., example="Казаков Олег Дмитриевич")
    departments: str = Field(..., example="Кафедра информационных технологий")


class Lesson(BaseModel):
    subjectName: str
    building: str
    startAt: str = Field(..., example="10:35:00")
    endAt: str = Field(..., example="12:10:00")
    classroom: str
    teacher: Optional[str] = None
    isLecture: bool
    teacherFullName: Optional[str] = None


class DaySchedule(BaseModel):
    MONDAY: Optional[List[Lesson]] = None
    TUESDAY: Optional[List[Lesson]] = None
    WEDNESDAY: Optional[List[Lesson]] = None
    THURSDAY: Optional[List[Lesson]] = None
    FRIDAY: Optional[List[Lesson]] = None
    SATURDAY: Optional[List[Lesson]] = None


class WeekSchedule(BaseModel):
    first_week: DaySchedule
    second_week: DaySchedule
