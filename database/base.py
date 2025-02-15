import datetime
import json
import re
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from config import engine, SCHEDULE_UPLOAD_DATE
from models.database.models import *

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)  # Пусть последнее останется


@asynccontextmanager
async def get_session():
    try:
        async with async_session() as session:
            yield session
    except:
        await session.rollback()
        raise
    finally:
        await session.close()


# Для FastApi Dependent
async def get_session_fastapi() -> AsyncSession:
    async with async_session(bind=engine) as session:
        yield session


async def db_init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def manage_groups(group_name):
    async with AsyncSession(bind=engine) as session:
        group_id = (
            await session.execute(select(Groups.id).where(Groups.name == group_name))
        ).scalar()
        if group_id is not None:
            return group_id
        else:
            new_group = Groups(name=group_name)
            session.add(new_group)
            await session.commit()
            await session.refresh(new_group)
            return new_group.id


async def search_group(user_query):
    pattern = r"[а-яА-ЯёЁ\-0-9]+"
    matches = re.findall(pattern, user_query)

    user_query = "".join(matches)
    user_query = "%" + user_query.upper() + "%"

    search_template = """
    WITH modified_groups AS (
    SELECT
        id,
        name,
        UPPER(REPLACE(REPLACE(REPLACE(name, '(', ''), ')', ''), '-', '')) AS group_name
    FROM groups
    )
    SELECT id, name
    FROM modified_groups
    WHERE group_name LIKE :val
    ORDER BY name
    """

    async with get_session() as session:
        search_query = await session.execute(
            search_template, params={"val": user_query}
        )
        search_results = search_query.fetchall()

    formatted_list = [{"id": item[0], "name": item[1]} for item in search_results]
    return formatted_list


async def get_raw_schedules():
    async with get_session() as session:
        search_query = await session.execute(
            select(Groups.id, Groups.rawSchedule).where(Groups.id > 0)
        )
        all_schedules = search_query.fetchall()
        return all_schedules


async def old_manage_subjects(subject_name, group_id):
    """
    Create subject or fetch subject and return subjectId
    """
    async with get_session() as session:
        "Если None по запросу поиска, то возвращаем"
        search_query = await session.execute(
            select(Subjects.id).where(
                Subjects.name == subject_name, Subjects.groupId == group_id
            )
        )
        search_result = search_query.scalar()
        if search_result is None:
            # Делаем вставку данных и возвращаем данные
            new_subject = Subjects(name=subject_name, groupId=group_id)
            session.add(new_subject)
            await session.commit()
            await session.refresh(new_subject)
            return new_subject.id
        else:
            return search_result


async def insert_schedule(group_id, schedule, is_forced=True):
    async with get_session() as session:
        query = await session.execute(select(Groups).where(Groups.id == group_id))
        group = query.scalar()
        group.rawSchedule = schedule
        group.scheduleVersion += 1
        if is_forced:
            group.forceUpdateVersion = group.scheduleVersion
        session.add(group)
        await session.commit()


async def db_reset_schedules(and_subjects=False):
    async with get_session() as session:
        await session.execute(delete(Lessons))
        await session.commit()
        if and_subjects:
            await session.execute(delete(Subjects))
            await session.commit()


async def db_drop_tables():
    async with engine.begin() as conn:
        lessons_table = Base.metadata.tables["lessons"]
        subjects_table = Base.metadata.tables["subjects"]
        groups_table = Base.metadata.tables["groups"]
        await conn.run_sync(lessons_table.drop)
        await conn.run_sync(subjects_table.drop)
        await conn.run_sync(groups_table.drop)


async def insert_lesson(lesson):
    async with get_session() as session:
        session.add(lesson)
        await session.commit()


async def up_schedule_version(group_id: int):
    async with get_session() as session:
        # Прочитать json из файла по ключу forceUpdateVersion и записать str(datetime.date)
        with open(SCHEDULE_UPLOAD_DATE, "r") as f:
            data = json.load(f)
        data["scheduleUploadDate"] = str(
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        with open(SCHEDULE_UPLOAD_DATE, "w") as f:
            json.dump(data, f, indent=4)

        query = await session.execute(select(Groups).where(Groups.id == group_id))
        group = query.scalar()
        group.scheduleVersion += 1
        await session.commit()


async def clean_schedules():
    async with get_session() as session:
        current_date = datetime.datetime.now() + datetime.timedelta(weeks=-4)
        delete_date = datetime.datetime.strptime(
            f'{current_date.year} {int(current_date.strftime("%V"))} 1', "%Y %W %w"
        ).date()

        await session.execute(delete(Lessons).where(Lessons.lessonDate < delete_date))
        await session.commit()


async def is_schedule_filled(group_id, monday_date):
    async with get_session() as session:
        saturday_date = monday_date + datetime.timedelta(days=5)
        # Если на дату есть уроки с subjectId принадлежащей группе X
        r = (
            await session.execute(
                select(Lessons.id)
                .join(Subjects)
                .filter(Subjects.groupId == group_id)
                .filter(Lessons.lessonDate.between(monday_date, saturday_date))
            )
        ).scalar()
        print(r)
        return r is not None


async def correct_subject_spelling(subject_name: str, group_id: int):
    """
    Из-за особенностей парсинга Excel бывают subjectName с длинным названием
     в некоторых случаях делают самостоятельный перенос через "тире" — "Тестовое назва-ние"
    Функция берет subjectName без пробелов и тире, ищет название предмета, в котором меньше тире
     если такое найдено, то заменяет subjectName у всех
    """
    sql_search_in_group = """
    WITH modified_subjects AS (
    SELECT
        id,
        name,
  		"groupId",
        REPLACE(REPLACE(name, ' ', ''), '-', '') AS modif_names
    FROM subjects
  	WHERE "groupId" = :groupid
    )
    SELECT id, name
    FROM modified_subjects
    WHERE modif_names = :modifiedsubjectname
    """
    sql_search_everywhere = """
    WITH modified_subjects AS (
    SELECT
        id,
        name,
        REPLACE(REPLACE(name, ' ', ''), '-', '') AS modif_names
    FROM subjects
    )
    SELECT id, name
    FROM modified_subjects
    WHERE modif_names = :modifiedsubjectname
    """
    modified_subjectname = subject_name.replace(" ", "").replace("-", "")
    async with get_session() as session:
        search_query = await session.execute(
            sql_search_in_group,
            params={"groupid": group_id, "modifiedsubjectname": modified_subjectname},
        )
        search_results = search_query.fetchall()
        subjects_in_group = [
            {"id": item[0], "name": item[1]} for item in search_results
        ]

        is_adding_current_subject = False
        if len(subjects_in_group) == 0:
            new_subject = Subjects(name=subject_name, groupId=group_id)
            session.add(new_subject)
            await session.commit()
            await session.refresh(new_subject)
        else:
            if subjects_in_group[0]["name"] != subject_name:
                is_adding_current_subject = True
        search_query = await session.execute(
            sql_search_everywhere, params={"modifiedsubjectname": modified_subjectname}
        )
        search_results = search_query.fetchall()
        subjects_with_typos = [
            {"id": item[0], "name": item[1]} for item in search_results
        ]
        if is_adding_current_subject:
            subjects_with_typos.append({"id": 0, "name": subject_name})
        if len(subjects_with_typos) > 1:
            best_subject_name = ""
            min_dashes_counter = 999
            for subject in subjects_with_typos:
                name = subject["name"]

                dashes_count = name.count("-")
                if dashes_count < min_dashes_counter:
                    min_dashes_counter = dashes_count
                    best_subject_name = name

            # Идем по всем полученным предметам и меняем им имя
            for subject in subjects_with_typos:
                if subject["id"] != 0:
                    subject_obj_query = select(Subjects).where(
                        Subjects.id == subject["id"]
                    )
                    subject_obj = await session.scalar(subject_obj_query)
                    subject_obj.name = best_subject_name
                    await session.commit()

        # Необходимо вернуть данные
        return new_subject.id if len(subjects_in_group) == 0 else subjects_in_group[0]['id']

