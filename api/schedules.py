import calendar
import datetime
import json
import re
from datetime import date
from typing import Optional

import jmespath
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from config import SCHEDULE_UPLOAD_DATE
from database.base import get_session_fastapi
from locals import loc
from models.api import responses
from models.database.models import Lessons, Subjects, Groups

schedules_router = APIRouter(tags=["Schedules"])


@schedules_router.get("/v2/lessons", responses={200: {"model": responses.Lessons}})
async def get_lessons(
    groupId: int,
    session: AsyncSession = Depends(get_session_fastapi),
    cache: Optional[bool] = Query(False, description="Enable caching max-age=600"),
):
    """
    Расписание на 2 недели в json
    """
    query = await session.execute(
        select(Groups.rawSchedule).where(Groups.id == groupId)
    )
    json_schedule = query.scalar()  # dict

    if json_schedule is None:
        # В приложении появится выбор группы(новый учебный год => индексы сменились)
        raise HTTPException(status_code=409, detail=f"Group {groupId} not found")

    # Цифровые индексы превращаем в строки типа MONDAY, TUESDAY, ...
    for week in json_schedule:
        new_schedule = {}
        for day, classes in json_schedule[week].items():
            day_number = int(day)
            day_name = calendar.day_name[
                day_number - 1
            ].upper()  # day_number - 1 для соответствия с индексами
            new_schedule[day_name] = classes
        json_schedule[week] = new_schedule

    response = JSONResponse(content=jsonable_encoder(json_schedule))
    if cache:
        response.headers["Cache-Control"] = "max-age=600, public"
    return response



@schedules_router.get(
    "/v2/teacherSearch",
    responses={
        200: {
            "model": responses.TeacherLocations,
            "description": "При заполнении всех полей кроме searchQuery",
        }
    },
)
async def find_teacher(
    search_query: Optional[str] = Query(
        None, alias="searchQuery", description="Поисковой запрос, регистр не важен"
    ),
    teacher: Optional[str] = Query(None, description="Точное совпадение"),
    date_from: Optional[date] = Query(None, alias="dateFrom"),
    date_to: Optional[date] = Query(None, alias="dateTo"),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Расписание преподавателя (на 3 недели если не указывать dateFrom и dateTo)
    """
    if teacher:
        if not is_valid_russian(teacher):
            raise HTTPException(detail="No results", status_code=404)

        all_json_schedule = await session.execute(
            select(Groups.name, Groups.rawSchedule)
        )

        query_template = """
            {
              first_week: {
                "1": first_week."1"[?teacher=='{teacher}'],
                "2": first_week."2"[?teacher=='{teacher}'],
                "3": first_week."3"[?teacher=='{teacher}'],
                "4": first_week."4"[?teacher=='{teacher}'],
                "5": first_week."5"[?teacher=='{teacher}'],
                "6": first_week."6"[?teacher=='{teacher}']
              },
              second_week: {
                "1": second_week."1"[?teacher=='{teacher}'],
                "2": second_week."2"[?teacher=='{teacher}'],
                "3": second_week."3"[?teacher=='{teacher}'],
                "4": second_week."4"[?teacher=='{teacher}'],
                "5": second_week."5"[?teacher=='{teacher}'],
                "6": second_week."6"[?teacher=='{teacher}']
              }
            }
        """
        search_query = query_template.replace("{teacher}", teacher).strip()
        search_expression = jmespath.compile(search_query)

        parse_results = {"first_week": {}, "second_week": {}}

        # TODO: Сделать group_name
        for group_data in all_json_schedule:
            json_schedule = group_data.rawSchedule
            # group_name = group_data.name
            search_results = search_expression.search(json_schedule)
            search_results = replace_none_with_empty(search_results)
            if search_results:
                for week in parse_results:
                    for day, subjects in search_results[week].items():
                        for subject in subjects:
                            # subject["groupName"] = group_name
                            del subject["subjectId"]  # Незачем
                        if day not in parse_results[week]:
                            parse_results[week][day] = []
                        parse_results[week][day].extend(subjects)

        # Удаление дубликатов и сортировка по времени
        for week in parse_results:
            for day in parse_results[week]:
                # Удаляем дубликаты
                unique_items = [
                    dict(t)
                    for t in {tuple(d.items()) for d in parse_results[week][day]}
                ]

                # Сортируем по startTime
                sorted_items = sorted(
                    unique_items,
                    key=lambda x: datetime.datetime.strptime(
                        x.get("startAt"), "%H:%M:%S"
                    ),
                )
                parse_results[week][day] = sorted_items

        start_date = date_from or date.today()
        end_date = date_to or (start_date + datetime.timedelta(days=21))

        response_data = []
        current_date = start_date
        while current_date <= end_date:
            weekday = current_date.weekday() + 1
            if weekday == 7:  # Пропускаем воскресенье
                current_date += datetime.timedelta(days=1)
                continue

            week_number = int(current_date.strftime("%V"))  # Номер недели
            week_type = "first_week" if week_number % 2 == 1 else "second_week"

            lessons_find = parse_results.get(week_type, {}).get(str(weekday), [])
            if lessons_find:
                for lesson in lessons_find:
                    lesson["lessonDate"] = current_date.strftime("%Y-%m-%d")
                    lesson["weekday"] = (
                        current_date.weekday() + 1
                    )  #  1 - понедельник, 6 - суббота
                response_data.extend(lessons_find)
            current_date += datetime.timedelta(days=1)

        response_data = {tuple(item.items()): item for item in response_data}.values()
        response_data = sorted(
            response_data, key=lambda x: (x["lessonDate"], x["startAt"])
        )
        return response_data

    elif search_query:
        return ["Функция временно недоступна"]  # В ожидании валидатора

        if not is_valid_russian(search_query):
            raise HTTPException(detail="No results", status_code=404)

        search_query = search_query.strip().title()
        search_expression = jmespath.compile(
            f"*.*[?contains(teacher, '{search_query}')].teacher"
        )
        all_json_schedule = await session.execute(select(Groups.rawSchedule))
        teachers_list = set()

        for group_data in all_json_schedule:
            json_schedule = group_data.rawSchedule
            search_results = search_expression.search(json_schedule)
            if search_results:
                filter_array = []  # Избавляемся от массивов в массивах
                for sublist in search_results:
                    for item in sublist:
                        if item:
                            filter_array.append(item)
                # В итоге filter_array = [[teachers first_week],[teachers second_week]]

                for item in filter_array:
                    teachers_list.update(item)

        return list(teachers_list)
    else:
        raise HTTPException(detail=loc("errors", "no_action"), status_code=400)


@schedules_router.get(
    "/scheduleVersion",
    responses={
        200: {
            "model": responses.ScheduleVersion,
            "description": "В новой версии приложения нужно прокидывать в headers DataVersion",
        }
    },
)
async def get_schedule_version(
    request: Request, groupId: int, session: AsyncSession = Depends(get_session_fastapi)
):
    """
    В headers есть "DataVersion"
    В новой версии приложения ответ в json теперь, а в старой — int
    """
    version = request.headers.get("DataVersion")
    if version is not None:
        query = await session.execute(
            select(Groups.scheduleVersion, Groups.forceUpdateVersion).where(
                Groups.id == groupId
            )
        )
        schedule_version = [dict(r._mapping) for r in query]
        return schedule_version[0]
    else:
        query = await session.execute(
            select(Groups.scheduleVersion).where(Groups.id == groupId)
        )
        schedule_version = query.scalar()
        return int(schedule_version)


@schedules_router.get("/scheduleUpdateDate")
async def get_schedule_update_date():
    """
    Для бота
    """
    with open(SCHEDULE_UPLOAD_DATE, "r") as f:
        data = json.load(f)
    return data


def is_valid_russian(text: str) -> bool:
    return bool(re.match(r"^[\w\s\.]+$", text))


def replace_none_with_empty(obj):
    """
    Запись вида "1": first_week."1"[?teacher=='{teacher}'] | [] вместо [] на сервере давал None
    """
    if isinstance(obj, dict):
        return {k: replace_none_with_empty(v) for k, v in obj.items()}
    return [] if obj is None else obj
