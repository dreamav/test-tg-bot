"""Модуль проверки обязательной подписки на Telegram-канал."""

import logging
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from config import config

logger = logging.getLogger(__name__)

ALLOWED_STATUSES = {
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.RESTRICTED,
}


async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Проверить, подписан ли пользователь на обязательный канал.
    Если проверка отключена в настройках или CHANNEL_ID не задан, возвращает True.
    """
    if not config.ENABLE_SUBSCRIPTION_CHECK or not config.CHANNEL_ID:
        return True

    try:
        member = await bot.get_chat_member(
            chat_id=config.CHANNEL_ID, user_id=user_id
        )
        return member.status in ALLOWED_STATUSES
    except Exception as exc:
        logger.warning(
            "Не удалось проверить подписку пользователя %s в канале %s: %s",
            user_id,
            config.CHANNEL_ID,
            exc,
        )
        # Если бота не добавили в админы канала или произошла ошибка доступа,
        # не блокируем пользователя наглухо, а логируем ошибку
        return False
