from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import Column
from sqlalchemy import Integer, String, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy_json import MutableJson

Base = declarative_base()


class Groups(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    rawSchedule = Column(MutableJson)
    scheduleVersion = Column(Integer, default=0)
    forceUpdateVersion = Column(Integer, default=0)
    scheduleUpdateDate = Column(DateTime, default=lambda: datetime.now(ZoneInfo("Europe/Moscow")))
