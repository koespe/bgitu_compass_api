"""
Здесь находятся роуты, которые временно необходимы для уверенности в целостности данных
для внедрения расписания для преподавателей.
Роуты не будут использованы в пользовательском интерфейсе. Они необходимы лишь для точечного ручного контроля.
"""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import paths_config
from database.base import get_session_fastapi
from models.api import responses
from models.database.models import Groups

checks_router = APIRouter(tags=["Temporary data checks"])


@checks_router.get("/checkMissingTeachers")
async def check_missing_teachers(
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Временный route через ChatGPT для проверки до сентября 2026

    Проверяет все группы в rawSchedule и проверяет наличие преподавателей в списке fullTeacherName
    Возвращает список групп с отсутствующими преподавателями
    """
    # Получаем список всех преподавателей из файла teachers_info
    teachers_info_path = Path(paths_config.teachers_info)
    if not teachers_info_path.exists():
        raise HTTPException(status_code=404, detail="Файл teachers_info не найден")

    with open(teachers_info_path, "r", encoding="utf-8") as f:
        teachers_data = json.load(f)

    # Создаем множество коротких имен преподавателей для быстрого поиска
    teacher_short_names = set()
    for teacher in teachers_data:
        full_name = teacher.get("name", "").strip()
        if full_name:
            # Преобразуем полное имя в короткое (например, "Иванов Иван Иванович" -> "Иванов И.И.")
            name_parts = full_name.split()
            if len(name_parts) >= 2:
                surname = name_parts[0]
                initials = "".join(f"{p[0]}." for p in name_parts[1:3])
                short_name = f"{surname} {initials}"
                teacher_short_names.add(short_name)

    # Получаем все группы с их расписаниями
    result = await session.execute(select(Groups.name, Groups.rawSchedule))
    groups_data = result.all()

    # Проверяем каждую группу на наличие преподавателей, которых нет в списке
    # Создаем словарь для отслеживания, в каких группах встречается каждый преподаватель
    teacher_to_groups = {}

    for group in groups_data:
        group_name = group.name
        raw_schedule = group.rawSchedule

        if not raw_schedule:
            continue

        missing_teachers_in_group = set()

        # Проходим по всем неделям и дням в расписании
        for week_name, week_schedule in raw_schedule.items():
            for day_name, day_lessons in week_schedule.items():
                for lesson in day_lessons:
                    teacher_name = lesson.get("teacher")
                    if teacher_name and teacher_name not in teacher_short_names:
                        missing_teachers_in_group.add(teacher_name)

        # Для каждого отсутствующего преподавателя в этой группе добавляем группу в список
        for teacher in missing_teachers_in_group:
            if teacher not in teacher_to_groups:
                teacher_to_groups[teacher] = []
            teacher_to_groups[teacher].append(group_name)

    # Формируем финальный результат, объединяя преподавателей по группам
    missing_teachers_result = []
    for teacher, groups in teacher_to_groups.items():
        missing_teachers_result.append({"group": ", ".join(groups), "unknownTeacher": [teacher]})

    return missing_teachers_result


@checks_router.get("/checkSuspiciousSubjects", response_model=responses.SuspiciousSubjectsResponse)
async def check_suspicious_subjects(
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Анализирует все группы в rawSchedule и собирает все subjectName
    Возвращает 30 самых длинных названий предметов с указанием групп, где они встречаются
    """
    # Получаем все группы с их расписаниями
    result = await session.execute(select(Groups.name, Groups.rawSchedule))
    groups_data = result.all()

    # Словарь для сбора предметов и групп, где они встречаются
    subject_to_groups = {}

    for group in groups_data:
        group_name = group.name
        raw_schedule = group.rawSchedule

        if not raw_schedule:
            continue

        # Проходим по всем неделям и дням в расписании
        for week_name, week_schedule in raw_schedule.items():
            for day_name, day_lessons in week_schedule.items():
                for lesson in day_lessons:
                    subject_name = lesson.get("subjectName")
                    if subject_name:
                        if subject_name not in subject_to_groups:
                            subject_to_groups[subject_name] = set()
                        subject_to_groups[subject_name].add(group_name)

    # Преобразуем в список объектов
    subjects_list = []
    for subject, groups in subject_to_groups.items():
        subjects_list.append({"subject": subject, "groups": sorted(list(groups))})

    # Сортируем по длине названия (по убыванию) и берем топ-30
    subjects_list.sort(key=lambda x: len(x["subject"]), reverse=True)
    top_30_subjects = subjects_list[:30]

    # Формируем ответ в нужном формате
    return responses.SuspiciousSubjectsResponse(
        approximateAccuracy=100,
        subjects=[
            responses.SuspiciousSubject(subject=item["subject"], groups=item["groups"]) for item in top_30_subjects
        ],
    )


@checks_router.get("/checkGroupRisk", response_model=responses.GroupRiskResponse)
async def check_group_risk(
    session: AsyncSession = Depends(get_session_fastapi),
):
    """
    Комплексная проверка групп на риски устаревания данных
    Возвращает список групп с разделением на высокий и средний риск
    """
    import re
    from datetime import datetime, timezone

    # Получаем все группы
    result = await session.execute(select(Groups.name, Groups.scheduleUpdateDate))
    groups_data = result.all()

    risk_items = []

    # === Высокий риск: поиск пар групп типа "ПРИ-201" и "ПРИ-201(А)" ===
    # Собираем все имена групп
    all_group_names = {group.name for group in groups_data if group.name}

    # Паттерн для поиска групп с суффиксом в скобках
    suffix_pattern = re.compile(r"^(.+)\(([А-Яa-zA-Z])\)$")

    # Множество для отслеживания уже добавленных групп в high risk
    high_risk_groups = set()

    for group_name in all_group_names:
        match = suffix_pattern.match(group_name)
        if match:
            base_name = match.group(1)  # Например, "ПРИ-201"
            # Проверяем, существует ли базовая группа без суффикса
            if base_name in all_group_names:
                # Добавляем обе группы в high risk
                if group_name not in high_risk_groups:
                    risk_items.append(
                        responses.GroupRiskItem(
                            risk="high",
                            groupName=group_name,
                            reason=f"Обнаружена парная группа {base_name}",
                        )
                    )
                    high_risk_groups.add(group_name)
                if base_name not in high_risk_groups:
                    risk_items.append(
                        responses.GroupRiskItem(
                            risk="high",
                            groupName=base_name,
                            reason=f"Обнаружена парная группа {group_name}",
                        )
                    )
                    high_risk_groups.add(base_name)

    # === Средний риск: группы с устаревшими scheduleUpdateDate ===
    # Собираем все scheduleUpdateDate (исключая None)
    update_dates = []
    group_dates = {}  # {group_name: scheduleUpdateDate}

    for group in groups_data:
        if group.name and group.scheduleUpdateDate is not None:
            update_dates.append(group.scheduleUpdateDate)
            group_dates[group.name] = group.scheduleUpdateDate

    if update_dates:
        # Вычисляем среднюю дату
        avg_timestamp = sum(update_dates) / len(update_dates)
        avg_date = datetime.fromtimestamp(avg_timestamp, tz=timezone.utc)

        # Порог значимого отставания — 30 дней в секундах
        threshold_seconds = 30 * 24 * 60 * 60

        # Находим группы с датой обновления значительно ниже средней
        for group_name, update_date in group_dates.items():
            time_diff = avg_timestamp - update_date
            if time_diff > threshold_seconds:
                # Форматируем даты для вывода
                group_date = datetime.fromtimestamp(update_date, tz=timezone.utc)

                # Форматируем в читаемом виде: "11 авг. 26"
                group_date_str = group_date.strftime("%d %b. %y")
                avg_date_str = avg_date.strftime("%d %b. %y")

                risk_items.append(
                    responses.GroupRiskItem(
                        risk="medium",
                        groupName=group_name,
                        reason=f"Дата обновления ({group_date_str}) значительно ниже средней ({avg_date_str})",
                    )
                )

    return risk_items
