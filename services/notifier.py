"""Модуль отправки уведомлений администратору и в канал с расписанием."""

import logging
from typing import Any
from aiogram import Bot
from config import config

logger = logging.getLogger(__name__)


async def notify_admin_new_booking(bot: Bot, appointment: dict[str, Any]) -> None:
    """Уведомить владельца бота (ID администратора) о новой записи."""
    if not config.ADMIN_ID:
        return

    text = (
        "<b>🔔 Новая запись на маникюр!</b>\n\n"
        f"👤 <b>Клиент:</b> {appointment['user_name']}\n"
        f"📞 <b>Телефон:</b> {appointment['phone']}\n"
        f"📅 <b>Дата:</b> {appointment['date']}\n"
        f"⏰ <b>Время:</b> {appointment['time']}\n"
        f"🆔 <b>Telegram ID:</b> <code>{appointment['user_id']}</code>\n"
        f"📝 <b>Номер записи:</b> #{appointment['id']}"
    )
    try:
        await bot.send_message(chat_id=config.ADMIN_ID, text=text)
    except Exception as exc:
        logger.error("Не удалось отправить уведомление администратору: %s", exc)


async def notify_channel_new_booking(bot: Bot, appointment: dict[str, Any]) -> None:
    """Отправить информацию о занятом слоте в отдельный канал с расписанием."""
    if not config.SCHEDULE_CHANNEL_ID:
        return

    text = (
        "<b>📅 Обновление расписания</b>\n\n"
        "💅 <b>Процедура:</b> Маникюр\n"
        f"📅 <b>Дата:</b> {appointment['date']}\n"
        f"⏰ <b>Время:</b> {appointment['time']}\n"
        "🔒 <b>Статус:</b> Забронировано"
    )
    try:
        await bot.send_message(chat_id=config.SCHEDULE_CHANNEL_ID, text=text)
    except Exception as exc:
        logger.error(
            "Не удалось отправить уведомление в канал с расписанием: %s", exc
        )


async def notify_admin_cancellation(
    bot: Bot, appointment: dict[str, Any], by: str = "client"
) -> None:
    """Уведомить администратора об отмене записи."""
    if not config.ADMIN_ID:
        return

    reason = "клиентом" if by == "client" else "мастером"
    text = (
        f"<b>❌ Запись #{appointment['id']} отменена {reason}!</b>\n\n"
        f"👤 <b>Клиент:</b> {appointment['user_name']}\n"
        f"📞 <b>Телефон:</b> {appointment['phone']}\n"
        f"📅 <b>Дата:</b> {appointment['date']}\n"
        f"⏰ <b>Время:</b> {appointment['time']}\n\n"
        "<i>Слот снова свободен для записи.</i>"
    )
    try:
        await bot.send_message(chat_id=config.ADMIN_ID, text=text)
    except Exception as exc:
        logger.error(
            "Не удалось отправить уведомление об отмене администратору: %s", exc
        )


async def notify_client_cancellation(bot: Bot, appointment: dict[str, Any]) -> None:
    """Уведомить клиента, если мастер отменил его запись."""
    text = (
        "<b>⚠️ Ваша запись отменена мастером</b>\n\n"
        f"📅 <b>Дата:</b> {appointment['date']}\n"
        f"⏰ <b>Время:</b> {appointment['time']}\n\n"
        "Если у вас возникли вопросы или вы хотите выбрать другое время, пожалуйста, свяжитесь с мастером или оформите новую запись."
    )
    try:
        await bot.send_message(chat_id=appointment["user_id"], text=text)
    except Exception as exc:
        logger.error("Не удалось уведомить клиента об отмене записи: %s", exc)
