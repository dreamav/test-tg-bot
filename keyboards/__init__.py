"""Пакет клавиатур."""

from keyboards.calendar_kb import generate_calendar_keyboard
from keyboards.user_kb import (
    cancel_input_kb,
    confirm_booking_kb,
    main_menu_kb,
    my_appointment_kb,
    phone_request_kb,
    portfolio_kb,
    prices_kb,
    remove_reply_kb,
    slots_kb,
    subscription_kb,
)
from keyboards.admin_kb import (
    admin_appointments_list_kb,
    admin_cancel_confirm_kb,
    admin_cancel_input_kb,
    admin_day_actions_kb,
    admin_delete_slots_kb,
    admin_menu_kb,
)

__all__ = [
    "generate_calendar_keyboard",
    "main_menu_kb",
    "prices_kb",
    "portfolio_kb",
    "subscription_kb",
    "slots_kb",
    "confirm_booking_kb",
    "my_appointment_kb",
    "cancel_input_kb",
    "phone_request_kb",
    "remove_reply_kb",
    "admin_menu_kb",
    "admin_day_actions_kb",
    "admin_delete_slots_kb",
    "admin_appointments_list_kb",
    "admin_cancel_confirm_kb",
    "admin_cancel_input_kb",
]
