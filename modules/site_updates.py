import datetime
import hashlib
import io
import json
import os
import re
import time
import urllib.parse

import aiohttp
import openpyxl
import xlrd
from aiohttp import BasicAuth
from bs4 import BeautifulSoup
from sqlalchemy import select

from config import paths_config
from config import settings
from database.base import async_session
from models.database.models import Groups
from modules.excel_parser import parse_cell

TELEGRAM_NOTIFICATION_URL_TEMPLATE = (
    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage?"
    f"chat_id={settings.administration_chat_id}&"
    f"text="
)

_is_site_updates_checker_running = False


def parse_links_bak_spo(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    links = []

    for button in soup.find_all("button"):
        onclick = button.get("onclick")
        if onclick and "window.location.href" in onclick:
            # Используем регулярку для точного поиска ссылки внутри кавычек (одинарных или двойных)
            # Это надежнее, чем rfind, если пробелы или кавычки изменятся
            match = re.search(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
            if match:
                link = match.group(1)
                full_link = urllib.parse.urljoin("https://bgitu.ru", link)
                links.append(full_link)

    return links


def parse_links_mag(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    links = []

    # Ищем сразу все теги <а>, независимо от того, где они лежат (в таблице или div)
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Проверяем расширение (lower() на случай .XLS)
        if href.lower().endswith((".xls", ".xlsx")):
            full_link = urllib.parse.urljoin("https://bgitu.ru", href)
            links.append(full_link)

    return links


async def get_all_links(session):
    targets = [
        ("https://bgitu.ru/studentu/raspisanie/ochnoe-obuchenie/", parse_links_bak_spo),
        ("https://bgitu.ru/studentu/raspisanie/spo/spo-raspisanie.php", parse_links_bak_spo),
        ("https://bgitu.ru/studentu/raspisanie/magistratura/", parse_links_mag),
    ]

    all_links = []
    for url, parser in targets:
        content = await fetch_url(session, url)
        if not content:
            continue

        links = parser(content)
        if not links:
            continue

        all_links.extend(links)

    return all_links


async def fetch_url(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content_type = response.headers.get("Content-Type", "")
                if (
                    "application/vnd.ms-excel" in content_type
                    or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in content_type
                ):
                    return await response.read()
                else:
                    return await response.text()  # Если это сайт
            else:
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ошибка {url}: {response.status}")
                return None
    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Ошибка {url}: {e}")
        return None


def calculate_hash(content):
    if content:
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.sha256(content).hexdigest()
    return None


async def get_file_hash(session, url):
    content = await fetch_url(session, url)
    return calculate_hash(content)


def minimize_filenames(filename: str):
    filename = filename.replace("Расписание учебных занятий", "")  # Так нагляднее
    filename = filename.replace("Расписание учебных занятий", "")  # Вместо "й" там какой-то спецсимвол
    filename = filename.replace("Расписание занятий", "")
    filename = filename.strip()
    return filename


def normalize_group_name(name: str) -> str:
    """
    Нормализует названия группы для сравнения (только в пределах функции `check_missing_groups`)
    """
    if not name:
        return ""
    name = name.strip().replace("/", "-").replace(" ", "").replace("спо", "СПО")
    return name


async def send_telegram_message(message):
    async with aiohttp.ClientSession() as session:
        telegram_url = TELEGRAM_NOTIFICATION_URL_TEMPLATE + urllib.parse.quote(message)
        await session.get(telegram_url)


async def check_site_files_updates(upload_all: bool = False):
    """
    Вместо async lock используем файловую блокировку для Gunicorn
    и глобальный флаг для предотвращения дублей внутри одного процесса
    """
    global _is_site_updates_checker_running

    if _is_site_updates_checker_running:
        return

    lock_file = os.path.join(paths_config.work_directory, "data", "updates", "site_updates.lock")
    try:
        # Атомарная проверка и создание файла (O_EXCL гарантирует, что только один процесс создаст файл)
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        # Если файл есть, проверяем его возраст (защита от "зависших" блокировок)
        if time.time() - os.path.getmtime(lock_file) < 240:  # 4 минуты (цикл каждые 5 мин)
            return
        # Если старый — обновляем время (touch)
        os.utime(lock_file, None)
    except Exception:
        return

    _is_site_updates_checker_running = True
    try:
        async with aiohttp.ClientSession() as session:
            all_links = await get_all_links(session)

            # Сайт считается недоступным, если не найдено ссылок
            if not all_links:
                return

            # При upload_all=True удаляем файл с хэшами, чтобы все файлы считались новыми
            hashes_file = paths_config.schedule_hashes
            previous_hashes = {}
            if upload_all:
                if os.path.exists(hashes_file):
                    os.remove(hashes_file)
            else:
                if os.path.exists(hashes_file):
                    with open(hashes_file, "r", encoding="utf-8") as f:
                        previous_hashes = json.load(f)

            current_hashes = previous_hashes.copy()
            files_to_process = []

            for link in all_links:
                file_hash = await get_file_hash(session, link)
                if file_hash:
                    current_hashes[link] = file_hash
                    if file_hash != previous_hashes.get(link):
                        files_to_process.append(link)

            # Формируем данные для валидатора и уведомления
            data_for_validator = []
            notification_messages = []
            for link in files_to_process:
                if match := re.match(r".*/(.*?)(\s*\.\w+)$", link):
                    filename = minimize_filenames(urllib.parse.unquote(match.group(1)).strip())
                    safe_link = urllib.parse.quote(link, safe="/:")

                    data_for_validator.append({"name": filename, "url": safe_link})
                    notification_messages.append(filename)

            # Отправляем запросы в валидатор
            if data_for_validator:
                async with session.post(
                    url=settings.validator_url + "schedule/upload",
                    auth=BasicAuth(login="uploader", password=settings.admin_password),
                    json=data_for_validator,
                ) as request:
                    request_status = request.status
                    if request_status == 200:
                        notification_messages.insert(0, f"Подтвердите новое расписание -> {settings.validator_url}\n")
                    else:
                        notification_messages = [f"Ошибка при отправке файлов на валидацию: status={request_status}"]

                if request_status == 200:
                    with open(paths_config.schedule_hashes, "w", encoding="utf-8") as f:
                        json.dump(current_hashes, f, indent=4, ensure_ascii=False)

            if notification_messages:
                await send_telegram_message("\n".join(notification_messages))
    finally:
        _is_site_updates_checker_running = False
        # Файл НЕ удаляем, чтобы другие воркеры Gunicorn (которых 3)
        # не запустились сразу после того, как этот закончил.
        # Он сам "протухнет" через 4 минуты.


async def check_missing_groups():
    """
    Проверяет группы в БД на наличие в файлах расписания с сайта.
    Отправляет уведомление в чат администрации о группах, которые есть в БД, но отсутствуют в файлах.
    """
    lock_file = os.path.join(paths_config.work_directory, "data", "updates", "missing_groups.lock")

    try:
        # Атомарное создание файла для предотвращения гонки процессов в Gunicorn
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
    except FileExistsError:
        # Если файлу меньше 10 минут, значит другой воркер уже работает или недавно закончил
        if time.time() - os.path.getmtime(lock_file) < 600:
            return
        os.utime(lock_file, None)
    except Exception:
        return

    try:
        async with aiohttp.ClientSession() as session:
            all_links = await get_all_links(session)

            if not all_links:
                return

            # Скачиваем все файлы и собираем группы из них
            groups_from_files = set()
            for link in all_links:
                content = await fetch_url(session, link)
                if content:
                    file_groups = get_groups_from_file(content, link)
                    for group in file_groups:
                        groups_from_files.add(normalize_group_name(group))

            if not groups_from_files:
                return

            async with async_session() as db_session:
                query = select(Groups.name)
                result = await db_session.execute(query)
                db_groups = result.scalars().all()

            db_groups_normalized = {normalize_group_name(group): group for group in db_groups}

            missing_groups = []
            for normalized_name, original_name in db_groups_normalized.items():
                if normalized_name not in groups_from_files:
                    missing_groups.append(original_name)

            if missing_groups:
                message = "⚠️ Группы, которые есть в БД, но не найдены в файлах расписания:\n\n"
                message += "\n".join(sorted(missing_groups))
                message += "\n\nДанные группы возможно устарели, если это так, то удалите группы в валидаторе."
                await send_telegram_message(message)
    finally:
        # Файл НЕ удаляем, чтобы опоздавшие воркеры увидели его и пропустили выполнение
        pass


def get_groups_from_file(file_content: bytes, url: str = "") -> list[str]:
    if file_content.startswith(b"PK"):
        wb = openpyxl.load_workbook(io.BytesIO(file_content))
        sheet = wb.worksheets[0]
        return _parse_sheet_groups(sheet, parser_type="xlsx")
    elif file_content.startswith(b"\xD0\xCF\x11\xE0"):
        wb = xlrd.open_workbook(file_contents=file_content)
        sheet = wb.sheet_by_index(0)
        return _parse_sheet_groups(sheet, parser_type="xls")
    else:
        print(f"[get_groups_from_file] Неизвестный формат файла: {url}")
        return []


def _parse_sheet_groups(sheet, parser_type: str) -> list[str]:
    groups = []

    if parser_type == "xlsx":
        cell_parser = lambda s, r, c: parse_cell(s, row=r + 1, col=c + 1)
        max_col_attr = sheet.max_column
        col_offset = 1
        row_offset = 1
    else:
        cell_parser = _parse_xls_cell
        max_col_attr = sheet.ncols
        col_offset = 0
        row_offset = 0

    groups_row = None
    # Ищем "корпус" более гибко (в разных столбцах и чуть больше строк)
    for row_number in range(1, 15) if parser_type == "xlsx" else range(15):
        for col_idx in [0, 1, 2]:
            cell = cell_parser(sheet, row_number - row_offset, col_idx)
            if cell is not None and str(cell).strip() and "корпус" in str(cell).lower():
                groups_row = row_number - row_offset
                break
        if groups_row is not None:
            break

    if groups_row is None:
        return groups

    schedule_start_row = None
    for row_number in range(groups_row + row_offset, 25):
        cell = cell_parser(sheet, row_number - row_offset, 0)
        if cell and "понедельник" in str(cell).lower():
            schedule_start_row = row_number - row_offset
            break

    if schedule_start_row is None:
        return groups

    start_col = 4 if parser_type == "xlsx" else 3
    empty_streak = 0
    # Не прерываемся на первой же пустой ячейке, идем до конца или до длинной серии пустот
    for group_column in range(start_col, max_col_attr + col_offset if parser_type == "xlsx" else max_col_attr):
        group_name = cell_parser(sheet, groups_row, group_column - col_offset)

        if group_name is None or str(group_name).strip() == "":
            empty_streak += 1
            if empty_streak > 10:
                break
            continue

        empty_streak = 0
        group_name_str = str(group_name).strip()

        if group_name_str.upper() in ("А", "Б"):
            subgroup = group_name_str
            base_name = cell_parser(sheet, groups_row - 1, group_column - col_offset) if groups_row > 0 else None
            if base_name:
                group_name_str = f"{str(base_name).strip()}({subgroup})"
            else:
                continue

        groups.append(group_name_str)

    return groups


def _parse_xls_cell(sheet, row, col):
    if row < 0 or col < 0:
        return None
    for merged_range in getattr(sheet, "merged_cells", []):
        if (
            hasattr(merged_range, "row_min")
            and merged_range.row_min <= row + 1 <= merged_range.row_max
            and merged_range.col_min <= col + 1 <= merged_range.col_max
        ):
            return sheet.cell_value(merged_range.row_min - 1, merged_range.col_min - 1)
    return sheet.cell_value(row, col)
