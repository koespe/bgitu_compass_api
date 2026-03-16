import json
from datetime import datetime, timezone

from sqlalchemy import text

from config import paths_config, settings


async def annual_data_reset():
    """
    Файл `schedule_hashes.json` не удаляем, потому что на сайте может долго еще висеть расписание
    """
    async with settings.engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE groups"))

    with open(paths_config.remote_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    config["lastResetTimestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    with open(paths_config.remote_config, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
