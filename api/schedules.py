import calendar
import json
from typing import Optional, List

from cachetools.func import ttl_cache
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings, paths_config
from database.base import get_session_fastapi, search_group
from models.api import responses
from models.database.models import Groups

schedules_router = APIRouter(tags=["Schedules"])


@schedules_router.get(
    "/groups",
    responses={
        200: {"model": List[responses.Groups]},
        404: {"description": "Группа не найдена"},
    },
)
async def get_groups(
    group_id: Optional[int] = Query(None, alias="groupId", description="Если зачем-то нужно получить название группы"),
    search_query: Optional[str] = Query(None, alias="searchQuery", description="Поисковой запрос, регистр не важен"),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Без аргументов — все группы
    """
    if search_query is not None:
        search_results = await search_group(search_query.replace("-", ""))
        return JSONResponse(search_results)

    query = select(Groups.id, Groups.name, Groups.scheduleUpdateDate)  # Все группы

    if group_id:
        query = query.where(Groups.id == group_id)

    result = await session.execute(query)
    groups_list = [dict(r._mapping) for r in result]

    if not groups_list and group_id:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    return JSONResponse(groups_list)


@schedules_router.get("/v2/lessons", deprecated=True)
async def get_lessons(
    groupId: int,
    cache: Optional[bool] = Query(False, description="Enable caching — header max-age=600"),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Будет отключено 1 сентября 2026
    Расписание на 2 недели в json "first/second week"-формате (с использованием логики swapWeeks)
    """
    query = await session.execute(select(Groups.rawSchedule).where(Groups.id == groupId))
    json_schedule = query.scalar()  # dict

    if json_schedule is None:
        # В приложении появится выбор группы(новый учебный год => индексы сменились)
        raise HTTPException(status_code=409, detail=f"Группа с id={groupId} не найдена")

    # Цифровые индексы превращаем в строки типа MONDAY, TUESDAY, ...
    for week in json_schedule:
        new_schedule = {}
        for day, lessons in json_schedule[week].items():
            day_number = int(day)
            day_name = calendar.day_name[day_number - 1].upper()  # day_number - 1 для соответствия с индексами
            for lesson in lessons:
                lesson["subjectId"] = 1  # Для совместимости со старыми версиями приложения

                teacher_short = lesson.get("teacher")
                lesson["teacherFullName"] = get_teacher_full_name(teacher_short) if teacher_short else None
            new_schedule[day_name] = lessons
        json_schedule[week] = new_schedule

    if settings.swap_weeks:
        json_schedule["first_week"], json_schedule["second_week"] = (
            json_schedule["second_week"],
            json_schedule["first_week"],
        )

    response = JSONResponse(content=jsonable_encoder(json_schedule))
    if cache:
        response.headers["Cache-Control"] = "max-age=600, public"
    return response


@schedules_router.get(
    "/v3/lessons",
    responses={
        200: {"model": responses.WeekSchedule, "description": "Расписание на 2 недели"},
        409: {"description": "Группа либо пропала, либо начался новый учебный год и индексы групп сменились"},
    },
)
async def get_lessons(
    groupId: int,
    cache: Optional[bool] = Query(False, description="Enable caching — header max-age=600"),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Расписание на 2 недели в json "first/second week"-формате так, как они записаны в файлах на сайте bgitu.ru

    Для правильности вычисления четности недели используйте termStartDate из GET /remoteConfig
    """
    query = await session.execute(select(Groups.rawSchedule).where(Groups.id == groupId))
    json_schedule = query.scalar()  # dict

    if json_schedule is None:
        # В приложении появится выбор группы(новый учебный год => индексы сменились)
        raise HTTPException(status_code=409, detail=f"Группа с id={groupId} не найдена")

    # Цифровые индексы превращаем в строки типа MONDAY, TUESDAY, ...
    for week in json_schedule:
        new_schedule = {}
        for day, lessons in json_schedule[week].items():
            day_number = int(day)
            day_name = calendar.day_name[day_number - 1].upper()  # day_number - 1 для соответствия с индексами
            for lesson in lessons:
                teacher_short = lesson.get("teacher")
                lesson["teacherFullName"] = get_teacher_full_name(teacher_short) if teacher_short else None
            new_schedule[day_name] = lessons
        json_schedule[week] = new_schedule

    response = JSONResponse(content=jsonable_encoder(json_schedule))
    if cache:
        response.headers["Cache-Control"] = "max-age=600, public"
    return response


@schedules_router.get(
    "/scheduleVersion",
    deprecated=True,
    responses={200: {"model": responses.ScheduleVersion}},
)
async def get_schedule_version(groupId: int, session: AsyncSession = Depends(get_session_fastapi)):
    try:
        query = await session.execute(
            select(Groups.scheduleVersion, Groups.forceUpdateVersion).where(Groups.id == groupId)
        )
        schedule_version = [dict(r._mapping) for r in query]
        return schedule_version[0]
    except IndexError:
        return Response(status_code=400)


@ttl_cache(maxsize=1, ttl=3600)
def get_teachers_mapping():
    if not paths_config.teachers_info.exists():
        return {}

    with open(paths_config.teachers_info, "r", encoding="utf-8") as f:
        teachers_data = json.load(f)

    mapping = {}
    for item in teachers_data:
        full_name = item.get("name", "").strip()
        if not full_name:  # На случай пробелов в таблицах
            continue

        # "Иванов Иван Иванович" —> "Иванов И.И."
        name_parts = full_name.split()
        if len(name_parts) >= 2:
            surname = name_parts[0]
            # Берем первый символ второго и третьего слова
            initials = "".join(f"{p[0]}." for p in name_parts[1:3])
            short_name = f"{surname} {initials}"
            mapping[short_name] = full_name

    return mapping


def get_teacher_full_name(short_name: str) -> Optional[str]:
    return get_teachers_mapping().get(short_name)


@schedules_router.get("/scheduleUpdateDate", deprecated=True)
async def get_schedule_update_date():
    """
    Это индикатор для приложения о смене учебного года и необходимости заново выбрать группу (для старых версий)

    scheduleUploadDate не играет роли, но это поле требует приложение (Field 'scheduleUploadDate' is required)
    """
    return {"userDataVersion": settings.user_data_version, "scheduleUploadDate": "2025-04-03 02:01:00"}
