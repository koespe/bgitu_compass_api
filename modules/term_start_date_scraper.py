import json
import re
from datetime import datetime

import aiohttp

from config import paths_config

BASE_URL = "https://bgitu.ru/"
PATTERN = r"var\s+_first_week_start\s*=\s*(\d+);"  # Регулярное выражение переменной _first_week_start


async def check_site_variable_updates():
    try:
        config_path = paths_config.remote_config
        config_data = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, timeout=15) as response:
                if response.status == 200:
                    html = await response.text()
                    match = re.search(PATTERN, html)
                    if match:
                        timestamp_ms = int(match.group(1))
                        timestamp_s = timestamp_ms / 1000.0
                        start_date = datetime.fromtimestamp(timestamp_s)

                        formatted_date = start_date.strftime("%Y-%m-%d")

                        if config_data.get("termStartDate") != formatted_date:
                            config_data["termStartDate"] = formatted_date

                            with open(config_path, "w", encoding="utf-8") as f:
                                json.dump(config_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
