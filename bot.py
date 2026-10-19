"""Главная точка входа для запуска Telegram-бота мастера маникюра."""

import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from config import config
from database.db import db
from handlers import admin_router, menu_router, user_router
from services.scheduler import restore_active_reminders, scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("bot")


async def setup_bot_commands(bot: Bot) -> None:
    """Установка команд бота в меню Telegram."""
    commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="admin", description="Панель администратора"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    """Основная функция инициализации и запуска бота."""
    logger.info("Запуск бота онлайн-записи к мастеру маникюра...")

    # Проверка наличия токена
    if not config.BOT_TOKEN or config.BOT_TOKEN.startswith("YOUR_"):
        logger.error(
            "ОШИБКА: Токен бота не указан в файле .env!\n"
            "Пожалуйста, откройте файл .env и установите BOT_TOKEN и ADMIN_ID."
        )
        return

    # Инициализация базы данных SQLite
    logger.info("Инициализация базы данных SQLite...")
    await db.init_db()

    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация роутеров
    dp.include_router(menu_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)

    # Запуск планировщика задач
    logger.info("Запуск планировщика задач (APScheduler)...")
    scheduler.start()

    # Восстановление активных напоминаний
    await restore_active_reminders(bot)

    # Регистрация команд в Telegram UI
    try:
        await setup_bot_commands(bot)
    except Exception as exc:
        logger.warning("Не удалось установить команды меню: %s", exc)

    logger.info(
        "Бот успешно запущен в режиме Long Polling! "
        "Вы можете открыть Telegram и написать боту /start."
    )

    try:
        # Пропуск накопившихся обновлений и запуск polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        logger.info("Остановка бота...")
        if scheduler.running:
            scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот успешно остановлен.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот выключен пользователем.")
