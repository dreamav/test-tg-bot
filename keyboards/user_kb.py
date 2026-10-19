"""Клавиатуры для взаимодействия с клиентом."""

from typing import Any
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню бота."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Записаться", callback_data="btn_book"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Моя запись", callback_data="btn_my_appointment"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💅 Прайсы", callback_data="btn_prices"
                ),
                InlineKeyboardButton(
                    text="🎨 Портфолио", callback_data="btn_portfolio"
                ),
            ],
        ]
    )


def portfolio_kb(pinterest_url: str) -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой перехода в портфолио."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Смотреть портфолио", url=pinterest_url
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню", callback_data="btn_to_main_menu"
                )
            ],
        ]
    )


def prices_kb() -> InlineKeyboardMarkup:
    """Клавиатура для сообщения с прайс-листом."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Записаться", callback_data="btn_book"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню", callback_data="btn_to_main_menu"
                )
            ],
        ]
    )


def subscription_kb(channel_link: str) -> InlineKeyboardMarkup:
    """Клавиатура для проверки обязательной подписки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Подписаться", url=channel_link)],
            [
                InlineKeyboardButton(
                    text="🔄 Проверить подписку",
                    callback_data="check_subscription",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню", callback_data="btn_to_main_menu"
                )
            ],
        ]
    )


def slots_kb(slots: list[dict[str, Any]], date_str: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора доступного времени для записи."""
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for slot in slots:
        btn = InlineKeyboardButton(
            text=f"⏰ {slot['time']}",
            callback_data=f"slot_pick:{slot['id']}:{date_str}",
        )
        row.append(btn)
        if len(row) == 3:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Выбрать другую дату", callback_data="btn_book"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def confirm_booking_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить запись", callback_data="confirm_booking"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить", callback_data="cancel_booking_process"
                )
            ],
        ]
    )


def my_appointment_kb(appointment_id: int) -> InlineKeyboardMarkup:
    """Клавиатура просмотра активной записи с кнопкой отмены."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить запись",
                    callback_data=f"user_cancel_apt:{appointment_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню", callback_data="btn_to_main_menu"
                )
            ],
        ]
    )


def cancel_input_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены ввода данных во время FSM."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отменить запись",
                    callback_data="cancel_booking_process",
                )
            ]
        ]
    )


def phone_request_kb() -> ReplyKeyboardMarkup:
    """Reply-клавиатура для быстрой отправки номера телефона."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_reply_kb() -> ReplyKeyboardRemove:
    """Удаление reply-клавиатуры."""
    return ReplyKeyboardRemove()
