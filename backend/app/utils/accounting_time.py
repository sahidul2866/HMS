from datetime import datetime
from zoneinfo import ZoneInfo
from app.core.config import get_settings


def today_local():
    return datetime.now(ZoneInfo(get_settings().hospital_timezone)).date()
