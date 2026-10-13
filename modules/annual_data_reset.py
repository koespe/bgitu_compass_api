import json
from datetime import date, datetime, timezone

from sqlalchemy import text

from config import paths_config, settings


async def annual_data_reset():
    today = date.today()
    if not date(today.year, 7, 15) <= today <= date(today.year, 8, 15):
        return

    async with settings.engine.begin() as conn:
        has_data = await conn.execute(text("SELECT EXISTS (SELECT 1 FROM groups)"))
        if not has_data.scalar():
            return

        await conn.execute(text("TRUNCATE TABLE groups"))

    with open(paths_config.remote_config, "r", encoding="utf-8") as f:
        config = json.load(f)

    config["lastResetTimestamp"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    with open(paths_config.remote_config, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
