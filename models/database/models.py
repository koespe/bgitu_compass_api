from sqlalchemy import Column, ForeignKey
from sqlalchemy import SmallInteger, ARRAY, Integer, BigInteger, String, Date, Time, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import JSON
from sqlalchemy_json import MutableJson

Base = declarative_base()


class Groups(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    alternativeName = Column(String)
    headmanId = Column(ARRAY(Integer))
    rawSchedule = Column(MutableJson)
    scheduleVersion = Column(Integer, default=0)
    forceUpdateVersion = Column(Integer, default=0)


class Subjects(Base):
    __tablename__ = 'subjects'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    groupId = Column(Integer, ForeignKey('groups.id'))


class Lessons(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True, index=True)
    subjectId = Column(Integer, ForeignKey('subjects.id'))
    lessonDate = Column(Date)
    weekday = Column(SmallInteger)
    startAt = Column(Time)  # Именно Time, хоть и в raw_schedule хранится в виде str
    endAt = Column(Time)  # так можно будет легко изменять данные и, наверное, сортировать
    building = Column(String)  # Здесь может быть дот
    classroom = Column(String)
    isLecture = Column(Boolean)
    teacher = Column(String)
    label = Column(String)


class Accounts(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    appUUID = Column(String, unique=True)
    groupId = Column(Integer)
    eosUserId = Column(Integer)
    telegramId = Column(BigInteger)
    fullName = Column(String)
    groupName = Column(String)
    eosGroupName = Column(String)
    firebaseToken = Column(String)
    hmsToken = Column(String)
    avatarUrl = Column(String)
    role = Column(String, default='Student')
    permissions = Column(ARRAY(String), default=['AddHomework'])
    accessToken = Column(String)
    refreshToken = Column(String)
    tokenExpireAt = Column(String)
    bio = Column(JSON, default={})  # NEW!!!!!!!!!!!!!!!!!1
    additionalData = Column(JSON, default={})


class Statistics(Base):
    __tablename__ = "statistics"

    userId = Column(Integer, primary_key=True, index=True)
    lastActivity = Column(Date)
    apiVersion = Column(Integer)
    groupName = Column(String)
    data = Column(JSON, nullable=True)
