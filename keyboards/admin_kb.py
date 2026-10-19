"""Клавиатуры для администратора/мастера."""

from typing import Any
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню панели администратора."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Управление расписанием",
                    callback_data="admin_schedule",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Записи на сегодня",
                    callback_data="admin_today_appointments",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Главное меню", callback_data="btn_to_main_menu"
                )
            ],
        ]
    )


def admin_day_actions_kb(
    date_str: str, is_closed: bool
) -> InlineKeyboardMarkup:
    """Меню действий для выбранной даты."""
    toggle_text = "🔓 Открыть день" if is_closed else "🔒 Закрыть день"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить слоты",
                    callback_data=f"admin_add_slots_prompt:{date_str}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить свободный слот",
                    callback_data=f"admin_del_slots_list:{date_str}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=f"admin_toggle_day:{date_str}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Список записей",
                    callback_data=f"admin_view_day:{date_str}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К календарю", callback_data="admin_schedule"
                )
            ],
        ]
    )


def admin_delete_slots_kb(
    slots: list[dict[str, Any]], date_str: str
) -> InlineKeyboardMarkup:
    """Клавиатура со списком свободных слотов для удаления."""
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    for slot in slots:
        btn = InlineKeyboardButton(
            text=f"🗑 {slot['time']}",
            callback_data=f"admin_del_slot_id:{slot['id']}:{date_str}",
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
                text="⬅️ Назад", callback_data=f"cal:admin:{date_str}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_appointments_list_kb(
    appointments: list[dict[str, Any]], date_str: str
) -> InlineKeyboardMarkup:
    """Клавиатура со списком активных записей для возможной отмены мастером."""
    keyboard: list[list[InlineKeyboardButton]] = []
    for apt in appointments:
        btn = InlineKeyboardButton(
            text=f"❌ Отменить: {apt['time']} — {apt['user_name']}",
            callback_data=f"admin_cancel_apt_ask:{apt['id']}:{date_str}",
        )
        keyboard.append([btn])

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад", callback_data=f"cal:admin:{date_str}"
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_cancel_confirm_kb(
    appointment_id: int, date_str: str
) -> InlineKeyboardMarkup:
    """Подтверждение отмены записи администратором."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚠️ Да, отменить запись",
                    callback_data=f"admin_cancel_apt_do:{appointment_id}:{date_str}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад", callback_data=f"admin_view_day:{date_str}"
                )
            ],
        ]
    )


def admin_cancel_input_kb(date_str: str) -> InlineKeyboardMarkup:
    """Отмена режима ввода слотов."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена", callback_data=f"cal:admin:{date_str}"
                )
            ]
        ]
    )
