import calendar
import json
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import jmespath
from cachetools import TTLCache, cached
from fastapi import APIRouter, HTTPException, Query
from fastapi import Depends
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import paths_config
from database.base import get_session_fastapi
from models.api import responses
from models.api.responses import Teacher
from models.database.models import Groups

teachers_router = APIRouter(tags=["Teachers"])
security = HTTPBearer()


@teachers_router.get("/teacherSchedule")
async def teacher_schedule(
    search_query: Optional[str] = Query(None, alias="searchQuery", description="Поисковой запрос, регистр не важен"),
    teacher: Optional[str] = Query(
        None, description="Точное совпадение, формат выдачи — first/second week, как в v2 и v3 /lessons"
    ),
    teacher_search: Optional[bool] = Query(
        True, alias="teacherSearch", description="Формат выдачи на 3 недели (как было в`/v2/teacherSearch`)"
    ),
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    При параметре `teacher_search = False`
    используйте termStartDate из GET /remoteConfig для правильности вычисления четности недели
    """
    if search_query:
        teachers_info = Path(paths_config.teachers_info)
        if not teachers_info.exists():
            raise HTTPException(
                status_code=404,
                detail='Обновите любую ячейку в валидаторе во вкладке "Преподаватели" для создания файла '
                "или выполните собственный POST запрос",
            )

        with open(teachers_info, "r", encoding="utf-8") as f:
            all_teachers = json.load(f)

        search_query = search_query.strip().lower()
        filtered_teachers = []

        for teacher in all_teachers:
            full_name = teacher["name"].lower()
            if search_query in full_name:
                filtered_teachers.append(teacher["name"])

        return filtered_teachers
    elif teacher:
        if not is_valid_russian(teacher):
            raise HTTPException(detail="Нет результатов", status_code=404)

        name_parts = teacher.split()
        surname = name_parts[0]
        initials = "".join(f"{p[0]}." for p in name_parts[1:3])
        teacher_short_name = f"{surname} {initials}"

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
        search_query = query_template.replace("{teacher}", teacher_short_name).strip()
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
                            del subject["teacher"]
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
                    key=lambda x: datetime.strptime(x.get("startAt"), "%H:%M:%S"),
                )
                parse_results[week][day] = sorted_items

        if not teacher_search:
            merged_schedule = merge_cross_group_classes_weekly(parse_results)

            # Для приложения: цифровые индексы превращаем в строки типа MONDAY, TUESDAY, ...
            for week in merged_schedule:
                new_schedule = {}
                for day, lessons in merged_schedule[week].items():
                    day_number = int(day)
                    day_name = calendar.day_name[day_number - 1].upper()
                    new_schedule[day_name] = lessons
                merged_schedule[week] = new_schedule

            return merged_schedule
        else:
            start_date = date.today()
            end_date = start_date + timedelta(days=21)
            current_date = start_date

            response_data = []
            while current_date <= end_date:
                weekday = current_date.weekday() + 1  # +1 потому что от 0 до 6
                if weekday == 7:  # Пропускаем воскресенье
                    current_date += timedelta(days=1)
                    continue

                week_type = get_week_type(current_date)
                lessons_find = parse_results.get(week_type, {}).get(str(weekday), [])
                if lessons_find:
                    for lesson in lessons_find:
                        lesson_data = lesson.copy()
                        lesson_data["lessonDate"] = current_date.strftime("%Y-%m-%d")
                        lesson_data["weekday"] = current_date.weekday() + 1  # 1 - понедельник, 6 - суббота
                        response_data.append(lesson_data)
                current_date += timedelta(days=1)

            response_data = {tuple(item.items()): item for item in response_data}.values()
            response_data = sorted(response_data, key=lambda x: (x["lessonDate"], x["startAt"]))
            return merge_cross_group_classes(response_data)
    else:
        raise HTTPException(detail="Не указано действие или ключ", status_code=400)


@teachers_router.get(
    "/v2/teacherSearch",
    deprecated=True,
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
            raise HTTPException(detail="Нет результатов", status_code=404)

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
                    key=lambda x: datetime.strptime(x.get("startAt"), "%H:%M:%S"),
                )
                parse_results[week][day] = sorted_items

        start_date = date_from or date.today()
        end_date = date_to or (start_date + timedelta(days=21))
        current_date = start_date
        response_data = []
        while current_date <= end_date:
            weekday = current_date.weekday() + 1  # +1 потому что от 0 до 6
            if weekday == 7:  # Пропускаем воскресенье
                current_date += timedelta(days=1)
                continue

            week_type = get_week_type(current_date)
            lessons_find = parse_results.get(week_type, {}).get(str(weekday), [])
            if lessons_find:
                for lesson in lessons_find:
                    lesson_data = lesson.copy()
                    lesson_data["lessonDate"] = current_date.strftime("%Y-%m-%d")
                    lesson_data["weekday"] = current_date.weekday() + 1  # 1 - понедельник, 6 - суббота
                    response_data.append(lesson_data)
            current_date += timedelta(days=1)

        response_data = {tuple(item.items()): item for item in response_data}.values()
        response_data = sorted(response_data, key=lambda x: (x["lessonDate"], x["startAt"]))
        return merge_cross_group_classes(response_data)

    elif search_query:
        if not is_valid_russian(search_query):
            raise HTTPException(detail="Нет результатов", status_code=404)

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
        raise HTTPException(detail="Не указано действие или ключ", status_code=400)


@teachers_router.get(
    "/teachersInfo",
    response_model=list[Teacher],
    responses={
        404: {"description": "Файл с преподавателями не найден. Необходимо обновить данные через валидатор"},
    },
)
async def get_teachers_info():
    """
    Полные ФИО преподавателей и их кафедры. Данные из таблицы в валидаторе
    """
    teachers_info = Path(paths_config.teachers_info)
    if not teachers_info.exists():
        raise HTTPException(
            status_code=404,
            detail='Обновите любую ячейку в валидаторе во вкладке "Преподаватели" для создания файла '
            "или выполните собственный POST запрос",
        )

    with open(teachers_info, "r", encoding="utf-8") as f:
        return json.load(f)


def is_valid_russian(text: str) -> bool:
    return bool(re.match(r"^[а-яА-ЯёЁ\s]+$", text))


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


def merge_cross_group_classes_weekly(schedule: dict) -> dict:
    """
    Объединяет одинаковые пары для разных групп в "first/second week"-формате teacherSchedule.
    В отличие от `merge_cross_group_classes`, тут нет полей `lessonDate` и `weekday`, также другая структура данных.
    """
    merged_schedule = {}

    # Идём по неделям: "first_week", "second_week"
    for week, days in schedule.items():
        merged_schedule[week] = {}
        # И по дням внутри недели: "1".."6" (как ключи в исходном формате)
        for day, lessons in days.items():
            unique_lessons = {}
            for lesson in lessons:
                # Ключ уникальности пары
                key = (
                    lesson.get("subjectName"),
                    lesson.get("building"),
                    lesson.get("startAt"),
                    lesson.get("endAt"),
                    lesson.get("classroom"),
                    lesson.get("isLecture"),
                )

                # Если видим эту пару впервые — кладём копию урока как "базовую" запись
                if key not in unique_lessons:
                    unique_lessons[key] = lesson.copy()
                    continue

                # Иначе это дубль той же пары, но для другой группы — добавляем groupName к уже накопленным группам
                current_groups = unique_lessons[key].get("groupName")
                new_group = lesson.get("groupName")

                # Если по какой-то причине groupName был пустой — просто проставим его.
                if not current_groups:
                    unique_lessons[key]["groupName"] = new_group
                    continue

                # Держим groupName как "Группа1, Группа2, ..." и не допускаем дублей:
                # - парсим текущую строку
                # - добавляем новую группу, если её ещё нет
                existing = [g.strip() for g in str(current_groups).split(",") if g.strip()]
                if new_group and new_group not in existing:
                    existing.append(new_group)
                unique_lessons[key]["groupName"] = ", ".join(existing)

            merged = list(unique_lessons.values())
            merged_schedule[week][day] = sorted(
                merged,
                key=lambda x: datetime.strptime(x.get("startAt"), "%H:%M:%S"),
            )
    return merged_schedule


@cached(TTLCache(maxsize=1, ttl=900))
def _get_term_start_date() -> date:
    try:
        with open(paths_config.remote_config, "r", encoding="utf-8") as f:
            config = json.load(f)
        return datetime.strptime(config["termStartDate"], "%Y-%m-%d").date()
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        start_year = date.today().year - 1 if date.today().month < 9 else date.today().year
        return date(start_year, 9, 1)


def get_week_type(current_date: date) -> str:
    term_start_date = _get_term_start_date()
    week_num = ((current_date - term_start_date).days // 7) + 1
    return "second_week" if week_num % 2 == 0 else "first_week"
