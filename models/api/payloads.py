from datetime import date
from typing import Optional, List

from pydantic import BaseModel, HttpUrl, Field



class UploadUpdate(BaseModel):
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: str


class RemoteConfigUpdate(BaseModel):
    swapWeeks: bool
    userDataVersion: int
    versionCode: int
    downloadUrl: Optional[str] = None
