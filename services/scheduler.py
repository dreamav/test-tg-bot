"""Модуль управления планировщиком задач (APScheduler) для автонапоминаний."""

import datetime
import logging
from typing import Any
from zoneinfo import ZoneInfo
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import config
from database.db import db

logger = logging.getLogger(__name__)

# Инициализация планировщика с нужным часовым поясом
scheduler = AsyncIOScheduler(timezone=ZoneInfo(config.TIMEZONE))


async def send_reminder_job(bot: Bot, appointment_id: int) -> None:
    """Задача отправки напоминания клиенту за 24 часа до визита."""
    try:
        apt = await db.get_appointment_by_id(appointment_id)
        if not apt:
            return

        # Напоминаем только если запись активна и еще не была отправлена
        if apt["is_active"] == 1 and apt["reminder_sent"] == 0:
            text = config.REMINDER_TEXT_TEMPLATE.format(time=apt["time"])
            await bot.send_message(chat_id=apt["user_id"], text=text)
            await db.mark_reminder_sent(appointment_id)
            logger.info("Напоминание для записи #%s успешно отправлено.", appointment_id)
    except Exception as exc:
        logger.error(
            "Ошибка при отправке напоминания для записи #%s: %s",
            appointment_id,
            exc,
        )


def schedule_appointment_reminder(bot: Bot, appointment: dict[str, Any]) -> bool:
    """
    Запланировать отправку напоминания за 24 часа до записи.
    Если до записи менее 24 часов — напоминание не создается.
    """
    try:
        date_str = appointment["date"]
        time_str = appointment["time"]
        tz = ZoneInfo(config.TIMEZONE)

        # Вычисляем время визита и время за 24 часа до него
        apt_datetime = datetime.datetime.strptime(
            f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz)

        reminder_time = apt_datetime - datetime.timedelta(hours=24)
        now = datetime.datetime.now(tz)

        # Если до визита осталось менее 24 часов (или дата уже в прошлом)
        if reminder_time <= now:
            logger.info(
                "Запись #%s создана менее чем за 24ч до визита (или в прошлом). Напоминание не создано.",
                appointment["id"],
            )
            return False

        job_id = f"reminder_{appointment['id']}"
        scheduler.add_job(
            send_reminder_job,
            "date",
            run_date=reminder_time,
            id=job_id,
            args=[bot, appointment["id"]],
            replace_existing=True,
        )
        logger.info(
            "Запланировано напоминание для записи #%s на %s",
            appointment["id"],
            reminder_time.isoformat(),
        )
        return True
    except Exception as exc:
        logger.error("Ошибка при планировании напоминания: %s", exc)
        return False


def cancel_appointment_reminder(appointment_id: int) -> None:
    """Удалить задачу напоминания при отмене записи."""
    job_id = f"reminder_{appointment_id}"
    try:
        job = scheduler.get_job(job_id)
        if job:
            scheduler.remove_job(job_id)
            logger.info("Напоминание для записи #%s удалено из планировщика.", appointment_id)
    except Exception as exc:
        logger.error("Ошибка при удалении напоминания #%s: %s", appointment_id, exc)


async def restore_active_reminders(bot: Bot) -> None:
    """Восстановление активных напоминаний из БД при перезапуске бота."""
    try:
        active_appointments = await db.get_active_appointments_for_reminders()
        restored_count = 0
        for apt in active_appointments:
            if schedule_appointment_reminder(bot, apt):
                restored_count += 1
        logger.info(
            "Восстановлено напоминаний из БД: %s из %s записей.",
            restored_count,
            len(active_appointments),
        )
    except Exception as exc:
        logger.error("Ошибка при восстановлении напоминаний из базы данных: %s", exc)
