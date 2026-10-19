"""Хэндлеры панели администратора/мастера маникюра."""

import datetime
import re
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from config import config
from database.db import db
from keyboards.admin_kb import (
    admin_appointments_list_kb,
    admin_cancel_confirm_kb,
    admin_cancel_input_kb,
    admin_day_actions_kb,
    admin_delete_slots_kb,
    admin_menu_kb,
)
from keyboards.calendar_kb import generate_calendar_keyboard
from services.notifier import notify_client_cancellation
from services.scheduler import cancel_appointment_reminder
from states.admin_states import AdminStates

router = Router(name="admin_router")


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора."""
    return config.ADMIN_ID != 0 and user_id == config.ADMIN_ID


async def _show_calendar_for_admin(
    message_or_callback: Message | CallbackQuery,
    year: int,
    month: int,
    is_edit: bool = True,
) -> None:
    """Отрисовка календаря в режиме администратора."""
    today = datetime.date.today()
    max_date = today + datetime.timedelta(days=30)

    start_date = today.strftime("%Y-%m-%d")
    end_date = max_date.strftime("%Y-%m-%d")

    closed_dates = await db.get_closed_dates(start_date, end_date)

    calendar_kb = generate_calendar_keyboard(
        year=year,
        month=month,
        closed_dates=closed_dates,
        is_admin=True,
        mode="admin",
    )

    text = (
        "<b>📅 Панель управления расписанием</b>\n\n"
        "Выберите дату для настройки слотов или закрытия дня:\n"
        "🔒 — день полностью закрыт для записи."
    )

    if isinstance(message_or_callback, CallbackQuery):
        if is_edit and message_or_callback.message:
            await message_or_callback.message.edit_text(
                text=text, reply_markup=calendar_kb
            )
        elif message_or_callback.message:
            await message_or_callback.message.answer(
                text=text, reply_markup=calendar_kb
            )
    else:
        await message_or_callback.answer(text=text, reply_markup=calendar_kb)


async def _show_day_management(
    message_or_callback: Message | CallbackQuery, date_str: str
) -> None:
    """Отображение карточки управления выбранным днем."""
    is_closed = await db.is_day_closed(date_str)
    all_slots = await db.get_all_slots_for_date(date_str)
    free_slots = [s for s in all_slots if s["is_booked"] == 0]
    booked_slots = [s for s in all_slots if s["is_booked"] == 1]

    status_str = "🔒 <b>Закрыт</b>" if is_closed else "🟢 <b>Открыт для записи</b>"
    slots_preview = ", ".join(s["time"] for s in all_slots) or "слоты не добавлены"

    text = (
        f"<b>⚙️ Управление днем: {date_str}</b>\n\n"
        f"Статус дня: {status_str}\n"
        f"Всего слотов: {len(all_slots)} (Свободно: {len(free_slots)}, Занято: {len(booked_slots)})\n"
        f"Расписание: <i>{slots_preview}</i>\n\n"
        "Выберите необходимое действие:"
    )

    kb = admin_day_actions_kb(date_str, is_closed)

    if isinstance(message_or_callback, CallbackQuery):
        if message_or_callback.message:
            await message_or_callback.message.edit_text(text=text, reply_markup=kb)
    else:
        await message_or_callback.answer(text=text, reply_markup=kb)


# ------------------ Вход в админ-панель ------------------


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    """Команда /admin — открытие панели администратора."""
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к панели администратора.")
        return

    text = (
        "<b>👑 Панель управления мастера</b>\n\n"
        "Здесь вы можете управлять рабочими днями, временными слотами и записями клиентов."
    )
    await message.answer(text=text, reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню панели администратора."""
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await callback.answer()
    text = (
        "<b>👑 Панель управления мастера</b>\n\n"
        "Выберите нужное действие:"
    )
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin_schedule")
async def callback_admin_schedule(callback: CallbackQuery, state: FSMContext) -> None:
    """Открытие календаря для администратора."""
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await callback.answer()
    today = datetime.date.today()
    await _show_calendar_for_admin(callback, today.year, today.month)


@router.callback_query(F.data.startswith("cal_nav:admin:"))
async def callback_admin_cal_nav(callback: CallbackQuery) -> None:
    """Навигация по календарю в админке."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await callback.answer()
    parts = callback.data.split(":")
    year, month = int(parts[2]), int(parts[3])
    await _show_calendar_for_admin(callback, year, month)


# ------------------ Действия с конкретным днем ------------------


@router.callback_query(F.data.startswith("cal:admin:"))
async def callback_admin_select_date(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Администратор выбрал дату в календаре."""
    await state.clear()
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await callback.answer()
    date_str = callback.data.split(":")[2]
    await _show_day_management(callback, date_str)


@router.callback_query(F.data.startswith("admin_toggle_day:"))
async def callback_admin_toggle_day(callback: CallbackQuery) -> None:
    """Переключение статуса дня (закрыть / открыть)."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    date_str = callback.data.split(":")[1]
    is_closed = await db.toggle_day_closed(date_str)
    status_msg = "🔒 День закрыт для записи." if is_closed else "🔓 День открыт для записи."
    await callback.answer(status_msg, show_alert=True)
    await _show_day_management(callback, date_str)


# ------------------ Добавление слотов ------------------


@router.callback_query(F.data.startswith("admin_add_slots_prompt:"))
async def callback_admin_add_slots_prompt(
    callback: CallbackQuery, state: FSMContext
) -> None:
    """Запрос на ввод времени новых слотов."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await callback.answer()
    date_str = callback.data.split(":")[1]
    await state.update_data(target_date=date_str)
    await state.set_state(AdminStates.waiting_for_slots_input)

    prompt = (
        f"Введите время слотов для даты <b>{date_str}</b> через запятую или пробел.\n\n"
        "Например:\n"
        "<code>10:00, 12:30, 15:00, 17:30</code>"
    )
    if callback.message:
        await callback.message.edit_text(
            text=prompt, reply_markup=admin_cancel_input_kb(date_str)
        )


@router.message(AdminStates.waiting_for_slots_input)
async def process_slots_input(message: Message, state: FSMContext) -> None:
    """Обработка введенных слотов времени."""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    date_str = data.get("target_date")
    if not date_str:
        await state.clear()
        return

    raw_text = message.text or ""
    # Поиск всех паттернов времени вида 10:00, 9:30 и т.д.
    matches = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", raw_text)
    if not matches:
        await message.answer(
            "Не удалось распознать время. Пожалуйста, введите время в формате <code>ЧЧ:ММ</code> (например, <code>10:00, 12:00, 14:30</code>):",
            reply_markup=admin_cancel_input_kb(date_str),
        )
        return

    # Нормализация формата (09:00, 10:00)
    normalized_times = [f"{int(h):02d}:{m}" for h, m in matches]
    # Убираем дубликаты с сохранением порядка
    unique_times = sorted(list(set(normalized_times)))

    added_count = await db.add_slots_batch(date_str, unique_times)
    await state.clear()

    await message.answer(
        f"✅ Успешно добавлено слотов: <b>{added_count}</b> на дату <b>{date_str}</b>!"
    )
    await _show_day_management(message, date_str)


# ------------------ Удаление свободных слотов ------------------


@router.callback_query(F.data.startswith("admin_del_slots_list:"))
async def callback_admin_del_slots_list(callback: CallbackQuery) -> None:
    """Отображение списка свободных слотов для удаления."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    date_str = callback.data.split(":")[1]
    all_slots = await db.get_all_slots_for_date(date_str)
    free_slots = [s for s in all_slots if s["is_booked"] == 0]

    if not free_slots:
        await callback.answer(
            "Нет свободных слотов для удаления.", show_alert=True
        )
        return

    await callback.answer()
    text = (
        f"<b>🗑 Удаление слотов на {date_str}:</b>\n\n"
        "Нажмите на слот, который хотите удалить:"
    )
    if callback.message:
        await callback.message.edit_text(
            text=text, reply_markup=admin_delete_slots_kb(free_slots, date_str)
        )


@router.callback_query(F.data.startswith("admin_del_slot_id:"))
async def callback_admin_del_slot_id(callback: CallbackQuery) -> None:
    """Удаление конкретного слота."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    parts = callback.data.split(":")
    slot_id = int(parts[1])
    date_str = parts[2]

    success = await db.delete_slot(slot_id)
    if success:
        await callback.answer("Слот успешно удален!", show_alert=True)
    else:
        await callback.answer(
            "Не удалось удалить слот (возможно, он уже занят или удален).",
            show_alert=True,
        )

    # Обновляем список свободных слотов
    all_slots = await db.get_all_slots_for_date(date_str)
    free_slots = [s for s in all_slots if s["is_booked"] == 0]
    if free_slots and callback.message:
        await callback.message.edit_text(
            f"<b>🗑 Удаление слотов на {date_str}:</b>\n\nВыберите слот для удаления:",
            reply_markup=admin_delete_slots_kb(free_slots, date_str),
        )
    else:
        await _show_day_management(callback, date_str)


# ------------------ Просмотр и отмена записей клиентов ------------------


@router.callback_query(F.data.startswith("admin_view_day:"))
async def callback_admin_view_day(callback: CallbackQuery) -> None:
    """Просмотр записей клиентов на выбранный день."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    date_str = callback.data.split(":")[1]
    appointments = await db.get_appointments_for_date(date_str)

    if not appointments:
        await callback.answer("На эту дату пока нет записей клиентов.", show_alert=True)
        return

    await callback.answer()
    lines = [f"<b>📋 Записи на {date_str}:</b>\n"]
    for apt in appointments:
        lines.append(
            f"⏰ <b>{apt['time']}</b> — {apt['user_name']} (📞 {apt['phone']})\n"
            f"   <i>ID: {apt['user_id']} | Запись #{apt['id']}</i>\n"
        )

    text = "\n".join(lines) + "\n<i>Чтобы отменить запись, выберите клиента ниже:</i>"

    if callback.message:
        await callback.message.edit_text(
            text=text,
            reply_markup=admin_appointments_list_kb(appointments, date_str),
        )


@router.callback_query(F.data.startswith("admin_cancel_apt_ask:"))
async def callback_admin_cancel_apt_ask(callback: CallbackQuery) -> None:
    """Подтверждение отмены записи администратором."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    await callback.answer()
    parts = callback.data.split(":")
    apt_id = int(parts[1])
    date_str = parts[2]

    apt = await db.get_appointment_by_id(apt_id)
    if not apt:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    text = (
        f"<b>⚠️ Подтверждение отмены записи #{apt_id}</b>\n\n"
        f"👤 Клиент: {apt['user_name']} ({apt['phone']})\n"
        f"📅 Дата и время: {apt['date']} в {apt['time']}\n\n"
        "Вы действительно хотите отменить эту запись? Клиент получит уведомление, а слот станет свободным."
    )
    if callback.message:
        await callback.message.edit_text(
            text=text, reply_markup=admin_cancel_confirm_kb(apt_id, date_str)
        )


@router.callback_query(F.data.startswith("admin_cancel_apt_do:"))
async def callback_admin_cancel_apt_do(
    callback: CallbackQuery, bot: Bot
) -> None:
    """Выполнение отмены записи администратором."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    parts = callback.data.split(":")
    apt_id = int(parts[1])
    date_str = parts[2]

    apt = await db.cancel_appointment_by_id(apt_id)
    if not apt:
        await callback.answer(
            "Не удалось отменить запись (возможно, уже была отменена).",
            show_alert=True,
        )
        await _show_day_management(callback, date_str)
        return

    await callback.answer("Запись отменена, слот освобожден.", show_alert=True)

    # Удаляем напоминание
    cancel_appointment_reminder(apt_id)

    # Уведомляем клиента
    await notify_client_cancellation(bot, apt)

    await _show_day_management(callback, date_str)


# ------------------ Записи на сегодня ------------------


@router.callback_query(F.data == "admin_today_appointments")
async def callback_admin_today(callback: CallbackQuery) -> None:
    """Просмотр записей на сегодня."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещен.", show_alert=True)
        return

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    appointments = await db.get_appointments_for_date(today_str)

    if not appointments:
        await callback.answer(
            f"На сегодня ({today_str}) записей нет.", show_alert=True
        )
        return

    await callback.answer()
    lines = [f"<b>📋 Записи на сегодня ({today_str}):</b>\n"]
    for apt in appointments:
        lines.append(
            f"⏰ <b>{apt['time']}</b> — {apt['user_name']} (📞 {apt['phone']})\n"
        )
    text = "\n".join(lines)
    if callback.message:
        await callback.message.edit_text(
            text=text, reply_markup=admin_day_actions_kb(today_str, False)
        )
