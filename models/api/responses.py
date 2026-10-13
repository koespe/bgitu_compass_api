import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, Field


class UpdateAvailability(BaseModel):
    size: int
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: HttpUrl


class Groups(BaseModel):
    id: int
    name: str
    scheduleUpdateDate: int


class RemoteConfig(BaseModel):
    termStartDate: datetime.date
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
    departments: list[str] = Field(..., example=["Кафедра информационных технологий"])


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


class ProfcomTimeRange(BaseModel):
    from_: str = Field(..., alias="from")
    to: str

    # разрешает и from_ в коде, и "from" из JSON
    model_config = {"populate_by_name": True}


class ProfcomDayRange(BaseModel):
    from_: int = Field(..., alias="from")
    to: int

    model_config = {"populate_by_name": True}


class ProfcomScheduleDefault(BaseModel):
    enabled: bool
    dayRange: ProfcomDayRange
    hours: Optional[ProfcomTimeRange] = None
    comment: Optional[str] = None


class ProfcomScheduleOverride(BaseModel):
    enabled: Optional[bool] = None
    dayRange: Optional[ProfcomDayRange] = None
    hours: Optional[ProfcomTimeRange] = None
    comment: Optional[str] = None


class ProfcomScheduleItem(BaseModel):
    default: ProfcomScheduleDefault
    overrides: dict[str, ProfcomScheduleOverride] = Field(default_factory=dict)


class ProfcomSchedules(BaseModel):
    materialAid: ProfcomScheduleItem
    studentScholarship: ProfcomScheduleItem


class ProfcomFullResponse(BaseModel):
    schedules: ProfcomSchedules
