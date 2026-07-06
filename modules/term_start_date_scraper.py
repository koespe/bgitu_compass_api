import json
from datetime import datetime, timedelta, date

import aiohttp
from bs4 import BeautifulSoup

from config import paths_config

BASE_URL = "https://bgitu.ru/"


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
            async with session.get(BASE_URL, timeout=15) as response:
                if response.status != 200:
                    return
                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        week_div = soup.find("div", class_="current-week")
        if not week_div:
            return

        week_text = week_div.get_text().lower()

        if "первая" in week_text:
            site_week_type = 1
        elif "вторая" in week_text:
            site_week_type = 2
        else:
            return

        # Расчет текущей четности недели по логике приложения: ??????????????????????????????????
        # 1-я неделя: week_num нечетный (1, 3, 5...)
        # 2-я неделя: week_num четный (2, 4, 6...)
        days_diff = (today - term_start).days
        week_num = (days_diff // 7) + 1
        current_week_type = 2 if week_num % 2 == 0 else 1

        # Если четность на сайте не совпадает с нашей, корректируем дату начала семестра
        if current_week_type != site_week_type:
            # Сдвигаем termStartDate на 7 дней назад, чтобы изменить четность текущей недели
            new_term_start = term_start - timedelta(days=7)
            config_data["termStartDate"] = new_term_start.strftime("%Y-%m-%d")

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

    except Exception:
        pass

"""
 > @modules/term_start_date_scraper.py надо изменить логку на более простую
   на сайте теперь есть кусок кода
   <div class="current-date-week">
       <br>
       <div class="current-date">
           28 апреля 2026, Вторник    </div>
       <br>
       <br class="tel_ots">
       <div class="current-week">
           <span class="just_text">Текущая неделя: </span> вторая    </div>
       <br>
       <br>
   </div>

   надо смотреть какая неделя на момент проверки по текущей логике. если по старой дате четность недели сходится с типом недели на сайте, то дату не
   менять.
"""
