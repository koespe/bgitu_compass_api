import re
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from config import settings
from models.database.models import *


engine = settings.engine
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # Пусть последнее останется


async def db_init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def manage_groups(group_name):
    async with AsyncSession(bind=engine) as session:
        group_id = (await session.execute(select(Groups.id).where(Groups.name == group_name))).scalar()
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
        search_query = await session.execute(search_template, params={"val": user_query})
        search_results = search_query.fetchall()

    formatted_list = [{"id": item[0], "name": item[1]} for item in search_results]
    return formatted_list


async def insert_schedule(group_id, schedule, is_forced=True):
    async with get_session() as session:
        query = await session.execute(select(Groups).where(Groups.id == group_id))
        group = query.scalar()
        group.rawSchedule = schedule

        group.scheduleVersion += 1
        if is_forced:  # Это проще, чем просить Елисея изменить логику в приложении
            group.forceUpdateVersion = group.scheduleVersion

        session.add(group)
        await session.commit()


async def db_truncate_groups():
    async with engine.begin() as conn:
        groups_table = Base.metadata.tables["groups"]
        await conn.run_sync(groups_table.truncate)


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
