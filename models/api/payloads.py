import datetime
from typing import List, Optional

from pydantic import BaseModel, HttpUrl, Field, field_validator


class UploadUpdate(BaseModel):
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: str


class RemoteConfigUpdate(BaseModel):
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

    @field_validator("teacherSearchWarningDateRanges", check_fields=False)
    @classmethod
    def validate_teacher_search_warning_date_ranges(cls, v):
        if v is None:
            return v

        for date_range in v:
            if not isinstance(date_range, list) or len(date_range) != 2:
                raise ValueError(
                    "Each date range in teacherSearchWarningDateRanges must contain exactly 2 dates in MM-DD format"
                )

            for date_str in date_range:
                if not isinstance(date_str, str) or len(date_str) != 5 or date_str[2] != "-":
                    raise ValueError(
                        f"Each date in teacherSearchWarningDateRanges must be in MM-DD format, got: {date_str}"
                    )

                try:
                    month, day = date_str.split("-")
                    month_int = int(month)
                    day_int = int(day)

                    if not (1 <= month_int <= 12):
                        raise ValueError(f"Month must be between 01 and 12, got: {month}")

                    if not (1 <= day_int <= 31):
                        raise ValueError(f"Day must be between 01 and 31, got: {day}")

                except ValueError as e:
                    if "invalid literal for int()" in str(e):
                        raise ValueError(
                            f"Invalid date format in teacherSearchWarningDateRanges: {date_str}. Must be MM-DD with numeric values."
                        )
                    raise e

        return v


class Teacher(BaseModel):
    name: str = Field(..., example="Казаков Олег Дмитриевич")
    departments: str = Field(..., example="Кафедра информационных технологий")


class TeachersInfo(BaseModel):
    teachers: list[Teacher]
