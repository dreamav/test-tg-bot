"""Модуль конфигурации бота."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    """Класс настроек приложения."""

    BOT_TOKEN: str
    ADMIN_ID: int
    CHANNEL_ID: str | None
    CHANNEL_LINK: str | None
    SCHEDULE_CHANNEL_ID: str | None
    ENABLE_SUBSCRIPTION_CHECK: bool
    REMINDER_TEXT_TEMPLATE: str
    DATABASE_PATH: str
    TIMEZONE: str


def load_config() -> Config:
    """Загрузка конфигурации из переменных окружения."""
    token = os.getenv("BOT_TOKEN", "").strip()
    
    admin_id_raw = os.getenv("ADMIN_ID", "0").strip()
    try:
        admin_id = int(admin_id_raw)
    except ValueError:
        admin_id = 0

    channel_id = os.getenv("CHANNEL_ID", "").strip()
    channel_link = os.getenv("CHANNEL_LINK", "").strip()
    schedule_channel_id = os.getenv("SCHEDULE_CHANNEL_ID", "").strip()

    enable_sub = os.getenv("ENABLE_SUBSCRIPTION_CHECK", "False").strip().lower() in (
        "true",
        "1",
        "yes",
    )

    reminder_template = os.getenv(
        "REMINDER_TEXT_TEMPLATE",
        "Напоминаем, что вы записаны на маникюр завтра в {time}.\nЖдём вас ❤️",
    ).strip().replace("\\n", "\n")

    db_path = os.getenv("DATABASE_PATH", "database.db").strip()
    timezone = os.getenv("TIMEZONE", "Europe/Moscow").strip()

    return Config(
        BOT_TOKEN=token,
        ADMIN_ID=admin_id,
        CHANNEL_ID=channel_id if channel_id else None,
        CHANNEL_LINK=channel_link if channel_link else None,
        SCHEDULE_CHANNEL_ID=schedule_channel_id if schedule_channel_id else None,
        ENABLE_SUBSCRIPTION_CHECK=enable_sub,
        REMINDER_TEXT_TEMPLATE=reminder_template,
        DATABASE_PATH=db_path,
        TIMEZONE=timezone,
    )


config = load_config()
