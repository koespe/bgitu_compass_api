"""
Скрипт запускается отдельно, из директории этого файла, скрипт в файле supervisord.conf
"""

import re
import urllib.parse
import aiohttp
import asyncio
import hashlib
import json

from aiohttp import BasicAuth
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import sys
import os
import time

# Жуткий костыль, но иначе на linux + supervisord не работает
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import paths_config
from config import settings

TELEGRAM_BOT_URL = (
    f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage?chat_id={settings.admin_tg_id}&text="
)

# In-memory флаг для уведомлений о пустых списках
last_empty_notification = {}


async def send_telegram_message(message):
    async with aiohttp.ClientSession() as session:
        telegram_url = TELEGRAM_BOT_URL + urllib.parse.quote(message)
        await session.get(telegram_url)


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
                print(f"Ошибка при получении {url}: {response.status}")
                return None
    except Exception as e:
        print(f"Ошибка при получении {url}: {e}")
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

    # Ищем сразу все теги <a>, независимо от того, где они лежат (в таблице или div)
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Проверяем расширение (lower() на случай .XLS)
        if href.lower().endswith((".xls", ".xlsx")):
            full_link = urllib.parse.urljoin("https://bgitu.ru", href)
            links.append(full_link)

    return links


async def get_all_links(session, notification_messages):
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
            await notify_empty_page(url, notification_messages)

        all_links.extend(links)

    return all_links


async def notify_empty_page(url, notification_messages):
    """
    Добавляет уведомление о пустой странице в список сообщений с cooldown.
    """
    current_time = time.time()
    last_notified = last_empty_notification.get(url, 0)
    if current_time - last_notified > 3600:  # Cooldown 1 час
        notification_messages.append(f"На странице {url} не найдено расписаний")
        last_empty_notification[url] = current_time


async def check_for_updates():
    async with aiohttp.ClientSession() as session:
        notification_messages = []
        all_links = await get_all_links(session, notification_messages)

        # Сайт считается недоступным, если не найдено ссылок
        if not all_links:
            return

        try:
            with open(paths_config.schedule_hashes, "r", encoding="utf-8") as f:
                previous_hashes = json.load(f)
        except FileNotFoundError:
            previous_hashes = {}

        current_hashes = previous_hashes.copy()  # Сохраняем старые хэши
        files_to_process = []

        for link in all_links:
            file_hash = await get_file_hash(session, link)
            if file_hash:
                current_hashes[link] = file_hash
                if file_hash != previous_hashes.get(link):
                    files_to_process.append(link)

        # Формируем данные для валидатора и уведомления
        data_for_validator = []
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


async def main():
    scheduler = AsyncIOScheduler()
    await check_for_updates()
    scheduler.add_job(check_for_updates, "interval", minutes=5)
    scheduler.start()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except:
        loop.close()
