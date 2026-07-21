from datetime import datetime, timezone

from sqlalchemy import Column
from sqlalchemy import Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy_json import MutableJson

Base = declarative_base()


class Groups(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    rawSchedule = Column(MutableJson)
    scheduleUpdateDate = Column(Integer, default=lambda: datetime.now(timezone.utc).timestamp())
