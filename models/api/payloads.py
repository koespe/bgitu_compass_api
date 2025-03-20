from datetime import date
from typing import Optional, List

from pydantic import BaseModel, HttpUrl, Field



class UploadUpdate(BaseModel):
    versionCode: int
    forceUpdateVersions: List[int]
    downloadUrl: str
