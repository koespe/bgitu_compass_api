import calendar
import datetime
import re
from datetime import date, timedelta
from typing import Optional

import jmespath
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.base import get_session_fastapi
from models.api import responses
from models.database.models import Groups

schedules_router = APIRouter(tags=["Schedules"])


@schedules_router.get("/v2/lessons")
async def get_lessons(
    groupId: int,
    session: AsyncSession = Depends(get_session_fastapi),
    cache: Optional[bool] = Query(False, description="Enable caching — header max-age=600"),
):
    """
    Расписание на 2 недели в json
    """
    query = await session.execute(select(Groups.rawSchedule).where(Groups.id == groupId))
    json_schedule = query.scalar()  # dict

    if json_schedule is None:
        # В приложении появится выбор группы(новый учебный год => индексы сменились)
        raise HTTPException(status_code=409, detail=f"Group {groupId} not found")

    # Цифровые индексы превращаем в строки типа MONDAY, TUESDAY, ...
    for week in json_schedule:
        new_schedule = {}
        for day, lessons in json_schedule[week].items():
            day_number = int(day)
            day_name = calendar.day_name[day_number - 1].upper()  # day_number - 1 для соответствия с индексами
            for lesson in lessons:
                lesson["subjectId"] = 1  # Для совместимости со старыми версиями приложения
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
    "/v2/teacherSearch",
    responses={
        200: {
            "model": responses.TeacherLocations,
            "description": "При заполнении всех полей кроме searchQuery",
        }
    },
)
async def find_teacher(
    search_query: Optional[str] = Query(None, alias="searchQuery", description="Поисковой запрос, регистр не важен"),
    teacher: Optional[str] = Query(None, description="Точное совпадение"),
    date_from: Optional[date] = Query(None, alias="dateFrom"),
    date_to: Optional[date] = Query(None, alias="dateTo"),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Расписание преподавателя
    dateFrom и dateTo — optional, без них возвращается расписание на 3 недели
    """
    # Проверка чтобы не положить API одним запросом
    if date_from and date_to:
        period_days = (date_to - date_from).days
        if period_days > 60:
            raise HTTPException(detail="Запрошенный период не может превышать 60 дней", status_code=400)

    if teacher:
        if not is_valid_russian(teacher):
            raise HTTPException(detail="No results", status_code=404)

        all_json_schedule = await session.execute(select(Groups.name, Groups.rawSchedule))

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

        for group_data in all_json_schedule:
            json_schedule = group_data.rawSchedule
            group_name = group_data.name
            search_results = search_expression.search(json_schedule)
            search_results = replace_none_with_empty(search_results)
            if search_results:
                for week in parse_results:
                    for day, subjects in search_results[week].items():
                        for subject in subjects:
                            subject["groupName"] = group_name
                        if day not in parse_results[week]:
                            parse_results[week][day] = []
                        parse_results[week][day].extend(subjects)

        for week in parse_results:
            for day in parse_results[week]:
                # Удаляем дубликаты из-за одной группы у потока
                unique_items = [dict(t) for t in {tuple(d.items()) for d in parse_results[week][day]}]

                # Сортируем по startTime
                sorted_items = sorted(
                    unique_items,
                    key=lambda x: datetime.datetime.strptime(x.get("startAt"), "%H:%M:%S"),
                )
                parse_results[week][day] = sorted_items

        start_date = date_from or date.today()
        end_date = date_to or (start_date + datetime.timedelta(days=21))
        current_date = start_date
        response_data = []
        while current_date <= end_date:
            weekday = current_date.weekday() + 1  # +1 потому что от 0 до 6
            if weekday == 7:  # Пропускаем воскресенье
                current_date += datetime.timedelta(days=1)
                continue

            week_type = get_week_type(current_date)
            lessons_find = parse_results.get(week_type, {}).get(str(weekday), [])
            if lessons_find:
                for lesson in lessons_find:
                    lesson_data = lesson.copy()
                    lesson_data["lessonDate"] = current_date.strftime("%Y-%m-%d")
                    lesson_data["weekday"] = current_date.weekday() + 1  # 1 - понедельник, 6 - суббота
                    response_data.append(lesson_data)
            current_date += datetime.timedelta(days=1)

        response_data = {tuple(item.items()): item for item in response_data}.values()
        response_data = sorted(response_data, key=lambda x: (x["lessonDate"], x["startAt"]))
        return merge_cross_group_classes(response_data)

    elif search_query:
        if not is_valid_russian(search_query):
            raise HTTPException(detail="No results", status_code=404)

        search_query = search_query.strip().title()
        search_expression = jmespath.compile(f"*.*[?contains(teacher, '{search_query}')].teacher")
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
        raise HTTPException(detail="No action or key provided", status_code=400)


@schedules_router.get(
    "/scheduleVersion",
    tags=["Will be deprecated soon"],
    responses={200: {"model": responses.ScheduleVersion}},
)
async def get_schedule_version(groupId: int, session: AsyncSession = Depends(get_session_fastapi)):
    """
    Will be deprecated soon
    """
    try:
        query = await session.execute(
            select(Groups.scheduleVersion, Groups.forceUpdateVersion).where(Groups.id == groupId)
        )
        schedule_version = [dict(r._mapping) for r in query]
        return schedule_version[0]
    except IndexError:
        return Response(status_code=400)


@schedules_router.get("/scheduleUpdateDate")
async def get_schedule_update_date():
    """
    Это индикатор для приложения о смене учебного года и необходимости заново выбрать группу (для старых версий)
    scheduleUploadDate не играет роли, но это поле требует приложение (Field 'scheduleUploadDate' is required)
    """
    return {"userDataVersion": settings.user_data_version, "scheduleUploadDate": "2025-04-03 02:01:00"}


def is_valid_russian(text: str) -> bool:
    """
    Защита от инъекций
    """
    return bool(re.match(r"^[\w\s.]+$", text))


def replace_none_with_empty(obj):
    """
    Запись вида "1": first_week."1"[?teacher=='{teacher}'] | [] вместо [] на сервере давал None
    """
    if isinstance(obj, dict):
        return {k: replace_none_with_empty(v) for k, v in obj.items()}
    return [] if obj is None else obj


def merge_cross_group_classes(lessons):
    """
    Если занятие для потока, то убираем дубликаты и записываем несколько групп в groupName
    """
    unique_lessons = {}
    for lesson in lessons:
        # Создаем ключ из всех полей, кроме groupName
        key = (
            lesson["subjectName"],
            lesson["building"],
            lesson["startAt"],
            lesson["endAt"],
            lesson["classroom"],
            lesson["teacher"],
            lesson["isLecture"],
            lesson["lessonDate"],
            lesson["weekday"],
        )

        # Если ключ уже существует, добавляем groupName к списку групп
        if key in unique_lessons:
            current_groups = unique_lessons[key]["groupName"]
            # Проверяем, является ли текущее значение уже строкой с запятыми
            if "," in current_groups:
                unique_lessons[key]["groupName"] += f", {lesson['groupName']}"
            else:
                # Первое объединение - преобразуем в строку с запятой
                unique_lessons[key]["groupName"] = f"{current_groups}, {lesson['groupName']}"
        else:
            # Если ключ встречается впервые, просто добавляем занятие в словарь
            unique_lessons[key] = lesson.copy()
    return list(unique_lessons.values())


def get_week_type(current_date: date) -> str:
    start_year = current_date.year - 1 if current_date.month < 9 else current_date.year
    start_date = date(start_year, 9, 1)

    if start_date.isoweekday() == 7:
        start_date += timedelta(days=1)

    week_num = ((current_date - start_date).days // 7) + 1
    is_second = (week_num % 2 == 0) != settings.swap_weeks
    return "second_week" if is_second else "first_week"
