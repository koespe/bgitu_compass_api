import json
import logging
from datetime import datetime, timedelta, date

import aiohttp
from bs4 import BeautifulSoup

from config import paths_config

logger = logging.getLogger(__name__)

TERM_START_URL = "https://bgitu.ru/"


async def check_site_variable_updates():
    try:
        config_path = paths_config.remote_config
        if not config_path.exists():
            return

        with open(config_path, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        term_start_str = config_data.get("termStartDate")
        if not term_start_str:
            return

        # Парсим текущую дату начала семестра (должна быть понедельником)
        term_start = datetime.strptime(term_start_str, "%Y-%m-%d").date()
        today = date.today()

        async with aiohttp.ClientSession() as session:
            async with session.get(TERM_START_URL, timeout=15) as response:
                if response.status != 200:
                    return
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        week_div = soup.find("div", class_="current-week")
        if not week_div:
            raise ValueError("div.current-week not found on site")

        week_text = week_div.get_text().lower()

        if "первая" in week_text:
            site_week_type = 1
        elif "вторая" in week_text:
            site_week_type = 2
        else:
            raise ValueError(f"Unknown week type in current-week: {week_text!r}")

        days_diff = (today - term_start).days
        current_week_type = 2 if (days_diff // 7) % 2 == 1 else 1

        if current_week_type != site_week_type:
            config_data["termStartDate"] = (term_start - timedelta(days=7)).strftime("%Y-%m-%d")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

    except ValueError as e:
        logger.warning("term_start_date_scraper: %s", e)
    except Exception:
        pass
