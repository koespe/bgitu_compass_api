import datetime
import io
import re
from typing import Union

import openpyxl
from openpyxl.cell import MergedCell, Cell
from openpyxl.worksheet.worksheet import Worksheet

from data import WEEKDAY_INDEX
from database.base import insert_schedule, manage_groups

NO_LESSONS_MAGISTRACY_STRING = "Дни самостоятельной"  # На всякий случай сократим, вдруг опечатка будет
WEEKDAY_COLUMN = 1
COLUMN_TIME_BUILDING_1 = 2
COLUMN_TIME_BUILDING_2 = 3


async def process_schedule_file(file):
    """
    Инициализация расписания из excel файлов в db.groups.rawSchedule
    """
    file = io.BytesIO(file.read())
    wb = openpyxl.load_workbook(file)
    sheet = wb.worksheets[0]

    groups_row = None
    for row_number in range(1, 10):
        cell = parse_cell(sheet, row=row_number, col=2)
        if cell is not None and cell != "":
            if "корпус" in cell.lower():
                groups_row = row_number
                break

    if groups_row is None:
        raise ValueError("Не найдена строка заголовка с группами и корпусами")

    schedule_start_row = None
    for row_number in range(groups_row, sheet.max_row + 1):
        cell = parse_cell(sheet, row=row_number, col=WEEKDAY_COLUMN)
        if cell and str(cell).strip().lower() in WEEKDAY_INDEX:
            schedule_start_row = row_number
            groups_row = schedule_start_row - 1
            break

    if schedule_start_row is None:
        raise ValueError("Не найдены дни недели в расписании")

    for group_column in range(4, sheet.max_column + 1):
        group_name = parse_group_name(sheet, group_column, groups_row)
        if not group_name:
            break
        group_id = await manage_groups(group_name)

        schedule_week = await parse_group_schedule(sheet, group_column, schedule_start_row)
        await insert_schedule(group_id, schedule_week)


def parse_group_name(sheet, group_column, groups_row):
    group_name = parse_cell(sheet=sheet, row=groups_row, col=group_column)
    if group_name is None:
        return None

    if group_name.upper().strip() in ("А", "Б"):  # Подгруппы
        subgroup = group_name
        base_group_name_cell = parse_cell(sheet, row=groups_row - 1, col=group_column)
        if base_group_name_cell:
            group_name = base_group_name_cell.strip() + f"({subgroup})"
        else:
            return None

    group_name = group_name.strip().replace("/", "-").replace("спо", "СПО")

    return group_name


async def parse_group_schedule(sheet, group_column, schedule_start_row):
    schedule_week = ensure_weekdays_keys({"first_week": {}, "second_week": {}})
    lesson_rows = []  # Номера строк текущей пары: одна или две.
    previous_key = None  # День и время текущей пары.

    for group_row in range(schedule_start_row, sheet.max_row + 1):
        weekday = parse_cell(sheet, row=group_row, col=WEEKDAY_COLUMN)
        weekday = str(weekday).strip().lower() if weekday else ""
        if weekday not in WEEKDAY_INDEX:
            break  # Дошли до пустой строки или примечаний после расписания.

        # Читаем время строки. Для объединённой ячейки parse_cell вернёт общее время.
        time_value = parse_cell(sheet, row=group_row, col=COLUMN_TIME_BUILDING_1)
        lesson_time = re.sub(r"\s+", "", str(time_value)) if time_value else ""
        key = (WEEKDAY_INDEX[weekday], lesson_time)

        # Другой день или время: сохраняем накопленные строки предыдущей пары.
        if key != previous_key:
            if lesson_rows:
                append_lesson(sheet, group_column, lesson_rows, previous_key[0], schedule_week)
            lesson_rows = []
            previous_key = key

        if not lesson_time:
            continue

        # При одинаковом дне и времени строки накапливаются для одной пары.
        lesson_rows.append(group_row)

    # Последнюю пару сохраняем здесь: следующей строки для её сохранения уже нет.
    if lesson_rows:
        append_lesson(sheet, group_column, lesson_rows, previous_key[0], schedule_week)

    return schedule_week


def append_lesson(sheet, group_column, lesson_rows, weekday_index, schedule_week):
    # Одна строка относится к обеим неделям, две — к первой и второй.
    for week_index, week_name in enumerate(("first_week", "second_week")):
        row = lesson_rows[0] if len(lesson_rows) == 1 else lesson_rows[week_index]
        lesson = parse_day(sheet, row=row, col=group_column, week_index=week_index)
        if lesson:
            schedule_week[week_name].setdefault(weekday_index, []).append(lesson)


def parse_day(sheet, row, col, week_index):
    cell = parse_cell(sheet, row=row, col=col, return_value=False)  # Ячейка со всеми ее свойствами
    cell_value: str = parse_cell(sheet, row=row, col=col, return_value=True)  # Plain text

    if (
        (cell_value is None)
        or (cell_value == "")
        or (cell_value == " ")
        or (NO_LESSONS_MAGISTRACY_STRING in str(cell_value))
    ):
        return None

    for i in range(2, 10):  # В тексте бывает много пробелов
        cell_value = cell_value.replace(" " * i, " ")
    cell_value = cell_value.strip().replace("\n", " ")

    if cell_value == "":
        return None

    # Проверка на второй корпус по цвету текста
    building = "1"
    if cell.font.color is not None:
        if cell.font.color.rgb == "FFFF0000" or cell.font.color.indexed == 10:
            building = "2"

    # Проверка на тип занятия по bold
    is_lecture = True if cell.font.bold else False

    # Следуя из корпуса получаем время
    column_time = COLUMN_TIME_BUILDING_1 if building == "1" else COLUMN_TIME_BUILDING_2
    start_at, end_at = (
        datetime.datetime.strptime(t, "%H.%M").strftime("%H:%M:%S")
        for t in parse_cell(sheet, row, column_time).split("-")
    )

    additional_data_matches = re.search(r"\[(.*?)]", cell_value)
    if additional_data_matches:
        additional_data = f" {additional_data_matches.group(1)}"
        cell_value = re.sub(r"\[.*?]", "", cell_value)  # Временное удаление этого текста
    else:
        additional_data = ""

    classroom = ""
    teacher = ""
    classrooms_count = cell_value.count("№") + cell_value.upper().count("ДОТ")
    if classrooms_count == 0:  # Преподаватель отсутствует и строчка из себя представляет название предмета
        is_lecture = False  # На всякий случай
    elif classrooms_count == 1:
        teacher = re.search(r"\((.*?)\)", cell_value).group(1)
        cell_value = re.sub(r"\([^)]*\)", "", cell_value)  # Убираем из строки преподавателя

        if "ДОТ" in cell_value.upper():
            building = "ДОТ"
            classroom = "ДОТ"
            cell_value = cell_value.replace("ДОТ", "").replace("дот", "")
        else:  # Это нормальная пара
            classroom = re.search(r"№(\S+)", cell_value).group(1)
            if "/" in classroom:  # "123/321" — разделение на первую/вторую недели
                classroom = classroom.split("/")[week_index]
            cell_value = re.sub(r"№\S+", "", cell_value).strip()  # Убираем из строки аудиторию
    elif classrooms_count == 2:
        # В этом случае первое значение — группа А, второе — Б
        teachers = [match.group(1) for match in re.finditer(r"\((.*?)\)", cell_value)]
        classrooms = [match.group(1) for match in re.finditer(r"№(\S+)", cell_value)]

        cell_value = re.sub(r"\([^)]*\)", "", cell_value)
        cell_value = re.sub(r"№\S+", "", cell_value).strip()
        cell_value = cell_value.replace(",", "")  # Между преподавателями остается запятая

        right_cell_value = parse_cell(sheet, row, col + 1)
        is_group_a = cell.value == right_cell_value
        classroom = classrooms[0 if is_group_a else 1]
        teacher = teachers[0 if is_group_a else 1]

    subject_name = cell_value.strip()
    subject_name = subject_name[0].upper() + subject_name[1:]
    subject_name += additional_data

    teacher = standardize_names(teacher)

    return {
        "subjectName": subject_name,
        "building": building,
        "startAt": start_at,
        "endAt": end_at,
        "classroom": classroom,
        "teacher": teacher,
        "isLecture": is_lecture,
    }


def parse_cell(sheet: Worksheet, row, col, using_merged=True, return_value=True) -> Union[str, MergedCell, Cell, None]:
    if row < 1 or col < 1:
        return None
    cell = sheet.cell(row=row, column=col)
    if using_merged:
        if isinstance(cell, MergedCell):
            for merged_range in sheet.merged_cells.ranges:
                if cell.coordinate in merged_range:
                    cell = sheet.cell(row=merged_range.min_row, column=merged_range.min_col)
                    break
        else:
            cell = sheet.cell(row, col)
        if return_value:
            value = cell.value  # Plain text
        else:
            return cell
    else:
        value = cell.value
    return value


def standardize_names(s):
    if s != "" and s is not None:
        s = s.replace(",", "")
        s = s.strip()

        # Замена множественных пробелов на один
        s = re.sub(r"\s+", " ", s)

        # Убираем пробелы между инициалами
        s = re.sub(r"([А-ЯЁA-Z])\.\s+([А-ЯЁA-Z]\.)", r"\1.\2", s)
    return s


def ensure_weekdays_keys(schedule_dict):
    """
    В магистратуре может не оказаться какого-то дня недели, так что добавляем их
    """
    for week in ["first_week", "second_week"]:
        for day in WEEKDAY_INDEX.values():
            if day not in schedule_dict[week]:
                schedule_dict[week][day] = []

    return schedule_dict
