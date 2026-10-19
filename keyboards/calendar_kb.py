"""Модуль генерации интерактивного inline-календаря."""

import calendar
import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MONTH_NAMES_RU = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]

WEEKDAY_NAMES_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def generate_calendar_keyboard(
    year: int,
    month: int,
    available_dates: set[str] | None = None,
    closed_dates: set[str] | None = None,
    is_admin: bool = False,
    mode: str = "user",
) -> InlineKeyboardMarkup:
    """
    Генерация inline-календаря на 1 месяц вперёд от текущей даты.
    :param year: Год
    :param month: Месяц
    :param available_dates: Множество дат (YYYY-MM-DD), где есть свободные слоты (для клиентов)
    :param closed_dates: Множество закрытых дат (для админа)
    :param is_admin: Режим администратора
    :param mode: Префикс ("user" или "admin")
    """
    if available_dates is None:
        available_dates = set()
    if closed_dates is None:
        closed_dates = set()

    today = datetime.date.today()
    max_date = today + datetime.timedelta(days=30)

    keyboard: list[list[InlineKeyboardButton]] = []

    # 1. Шапка: Название месяца и года, стрелки переключения
    prev_month_date = (
        datetime.date(year, month, 1) - datetime.timedelta(days=1)
    ).replace(day=1)
    next_month_date = (
        datetime.date(year, month, 28) + datetime.timedelta(days=5)
    ).replace(day=1)

    can_go_prev = prev_month_date >= today.replace(day=1)
    can_go_next = next_month_date <= max_date.replace(day=1)

    nav_row = [
        InlineKeyboardButton(
            text="◀️" if can_go_prev else " ",
            callback_data=(
                f"cal_nav:{mode}:{prev_month_date.year}:{prev_month_date.month}"
                if can_go_prev
                else "cal_ignore"
            ),
        ),
        InlineKeyboardButton(
            text=f"{MONTH_NAMES_RU[month]} {year}", callback_data="cal_ignore"
        ),
        InlineKeyboardButton(
            text="▶️" if can_go_next else " ",
            callback_data=(
                f"cal_nav:{mode}:{next_month_date.year}:{next_month_date.month}"
                if can_go_next
                else "cal_ignore"
            ),
        ),
    ]
    keyboard.append(nav_row)

    # 2. Дни недели
    weekdays_row = [
        InlineKeyboardButton(text=day, callback_data="cal_ignore")
        for day in WEEKDAY_NAMES_RU
    ]
    keyboard.append(weekdays_row)

    # 3. Сетка дней
    month_calendar = calendar.monthcalendar(year, month)
    for week in month_calendar:
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="cal_ignore"))
                continue

            current_date = datetime.date(year, month, day)
            date_str = current_date.strftime("%Y-%m-%d")

            # Проверяем диапазон [today .. max_date]
            in_range = today <= current_date <= max_date

            if not in_range:
                row.append(
                    InlineKeyboardButton(text=" ", callback_data="cal_ignore")
                )
                continue

            if is_admin:
                # В режиме админа отображаем индикатор закрытого дня
                is_closed = date_str in closed_dates
                label = f"{day}🔒" if is_closed else str(day)
                row.append(
                    InlineKeyboardButton(
                        text=label, callback_data=f"cal:{mode}:{date_str}"
                    )
                )
            else:
                # В режиме пользователя: кликабельны только даты со свободными слотами
                has_slots = date_str in available_dates
                if has_slots:
                    row.append(
                        InlineKeyboardButton(
                            text=f"🟢 {day}", callback_data=f"cal:{mode}:{date_str}"
                        )
                    )
                else:
                    row.append(
                        InlineKeyboardButton(
                            text=str(day), callback_data="cal_no_slots"
                        )
                    )
        keyboard.append(row)

    # 4. Кнопка возврата
    back_callback = "btn_to_main_menu" if not is_admin else "admin_menu"
    keyboard.append(
        [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback)]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
