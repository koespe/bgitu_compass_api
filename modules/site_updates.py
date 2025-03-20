import re
import urllib.parse

import aiohttp
import asyncio
import hashlib
import json
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import paths_config
from config import settings

""" Скрипт необходимо запускать в директории проекта, а не из папки modules

; supervisor config file
[program:bgitu-updates]
command=/home/user/bgitu_api/venv/bin/python3 modules/site_updates.py
directory=/home/user/bgitu_api
autostart=true
autorestart=true
redirect_stdout=true
redirect_stderr=true
"""

TELEGRAM_BOT_URL = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage?chat_id={settings.admin_tg_id}&text="
VALIDATOR_URL = "https://service.bgitu-compass.ru/"

async def fetch_url(session, url):
    """
    Асинхронно извлекает содержимое по заданному URL.
    """
    try:
        async with session.get(url) as response:
            if response.status == 200:
                if "application/vnd.ms-excel" in response.headers.get("Content-Type", ""):
                    return await response.read()  # Читаем как бинарный файл
                else:
                    try:
                        return await response.text()  # Пытаемся читать как текст с автоопределением кодировки
                    except UnicodeDecodeError:
                        return await response.read()  # Если не удалось, читаем как бинарный файл
            else:
                print(f"Ошибка при получении {url}: {response.status}")
                return None
    except aiohttp.ClientError as e:
        print(f"Ошибка клиента при получении {url}: {e}")
        return None
    except Exception as e:
        print(f"Неизвестная ошибка при получении {url}: {e}")
        return None


def calculate_hash(content):
    """
    Вычисляет SHA-256 хеш содержимого.
    """
    if content:
        if isinstance(content, str):
            content = content.encode("utf-8")  # Кодируем строку в байты
        return hashlib.sha256(content).hexdigest()
    return None


async def process_url(session, url, results):
    """
    Обрабатывает один URL, вычисляя хеш.
    """
    content = await fetch_url(session, url)
    if content:
        hash_value = calculate_hash(content)
        results[url] = hash_value
        return True  # Возвращаем True, если успешно обработали URL
    return False  # Возвращаем False, если не удалось обработать URL


def parse_links_bak(html_content):
    """
    Извлекает ссылки из HTML-кода главной страницы.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    fin = []
    # Ищем все блоки с классом "block"
    for block in soup.find_all("div", class_="block"):
        # В каждом блоке ищем div с классом "butt_class"
        butt_class_div = block.find("div", class_="butt_class")
        if butt_class_div:
            # Внутри "butt_class" ищем все кнопки
            for button in butt_class_div.find_all("button"):
                # Получаем значение атрибута onclick
                onclick = button.get("onclick")
                if onclick:
                    # Извлекаем ссылку из onclick
                    start = onclick.find("/studentu")
                    end = onclick.rfind("'")
                    if start != -1 and end != -1:
                        link = onclick[start:end]
                        fin.append("https://bgitu.ru" + link)
    return fin


def parse_links_spo(html_content):
    """
    Извлекает ссылки из HTML-кода страницы СПО.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    fin = []

    # Ищем ссылки в кнопках
    buttons_div = soup.find("div", class_="butt_style")
    if buttons_div:
        buttons = buttons_div.find_all("button")
        for button in buttons:
            onclick = button.get("onclick")
            if onclick:
                start = onclick.find("/studentu")
                end = onclick.rfind("'")
                if start != -1 and end != -1:
                    link = onclick[start:end]
                    fin.append("https://bgitu.ru" + link)
    return fin


def parse_links_mag(html_content):
    """
    Извлекает ссылки на XLS и XLSX файлы из HTML-кода страницы магистратуры.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    links = []

    # Ищем все ссылки в таблице
    table_rows = soup.find_all("tr")
    for row in table_rows:
        # Находим все ссылки в ячейках
        link_tag = row.find("a")
        if link_tag and link_tag.get("href"):
            href = link_tag.get("href")
            if href.endswith((".xls", ".xlsx")):
                links.append("https://bgitu.ru" + href)

    return links


async def get_all_links(session):
    """
    Получает все ссылки на файлы с БАК, СПО и МАГ
    """
    bak_url = "https://bgitu.ru/studentu/raspisanie/ochnoe-obuchenie/"
    spo_url = "https://bgitu.ru/studentu/raspisanie/spo/spo-raspisanie.php"
    mag_url = "https://bgitu.ru/studentu/raspisanie/magistratura/"

    html_content_main = await fetch_url(session, bak_url)
    links_main = parse_links_bak(html_content_main) if html_content_main else []

    html_content_spo = await fetch_url(session, spo_url)
    links_spo = parse_links_spo(html_content_spo) if html_content_spo else []

    html_content_mag = await fetch_url(session, mag_url)
    links_mag = parse_links_mag(html_content_mag) if html_content_mag else []
    return links_main + links_spo + links_mag


async def check_for_updates():
    """
    Проверяет наличие обновлений в расписании и отправляет уведомления.
    """
    async with aiohttp.ClientSession() as session:
        all_links = await get_all_links(session)
        current_hashes = {}
        new_files = []
        changed_files = []

        # Загружаем предыдущие хеши из файла
        try:
            with open(paths_config.schedule_hashes, "r", encoding="utf-8") as f:
                previous_hashes = json.load(f)
        except FileNotFoundError:
            previous_hashes = {}

        # Обрабатываем каждую ссылку и сравниваем хеши
        for link in all_links:
            if await process_url(session, link, current_hashes):
                current_hash = current_hashes.get(link)
                if link not in previous_hashes:
                    new_files.append(link)
                elif current_hash != previous_hashes.get(link):
                    changed_files.append(link)

        # Если есть новые или измененные файлы, отправляем уведомление и запрос в валидатор
        data_for_validator = []
        for link in new_files or changed_files:
            filename = re.match(r".*/(.*?)(\s*\.\w+)$", link).group(1)
            filename = filename.strip()
            safe_link = urllib.parse.quote(link, safe="/:")
            data_for_validator.append({"name": filename, "url": safe_link})

            await send_telegram_message(f"Новый файл: {filename}%0A%0A Ссылка: {safe_link}")
            await asyncio.sleep(1)

        # Сохраняем текущие хеши в файл
        with open(paths_config.schedule_hashes, "w", encoding="utf-8") as f:
            json.dump(current_hashes, f, indent=4, ensure_ascii=False)

        if data_for_validator:
            request = await session.post(
                url=settings.validator_url + "schedule/upload",
                headers={"Authorization": settings.admin_password},
                json=data_for_validator,
            )
            if request.status == 200:
                await send_telegram_message(f"Подтвердите новое расписание -> " + settings.validator_url)
            elif request.status == 504:
                await send_telegram_message(f"Новое расписание отправлено (504)")
            else:
                await send_telegram_message(f"Ошибка при отправке файлов на валидацию: status={request.status}")


async def send_telegram_message(message):
    """
    Отправляет сообщение в Telegram.
    """
    async with aiohttp.ClientSession() as session:
        telegram_url = TELEGRAM_BOT_URL + message
        try:
            await session.get(telegram_url)  # Просто отправляем GET запрос
        except Exception:
            pass


async def main():
    """
    Основная функция для запуска планировщика.
    """
    scheduler = AsyncIOScheduler()
    await check_for_updates()
    scheduler.add_job(check_for_updates, "interval", minutes=5)
    scheduler.start()

    print("Планировщик запущен. Ожидание событий...")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        print("Программа завершена.")
    finally:
        loop.close()
