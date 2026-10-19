"""Хэндлеры записи клиента, выбора слотов, FSM и отмены записи."""

import datetime
import re
from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from config import config
from database.db import db
from keyboards.calendar_kb import generate_calendar_keyboard
from keyboards.user_kb import (
    cancel_input_kb,
    confirm_booking_kb,
    main_menu_kb,
    my_appointment_kb,
    phone_request_kb,
    remove_reply_kb,
    slots_kb,
    subscription_kb,
)
from services.notifier import (
    notify_admin_cancellation,
    notify_admin_new_booking,
    notify_channel_new_booking,
)
from services.scheduler import (
    cancel_appointment_reminder,
    schedule_appointment_reminder,
)
from services.subscription import check_user_subscription
from states.user_states import BookingStates

router = Router(name="user_router")


async def _show_calendar_for_user(
    message_or_callback: Message | CallbackQuery,
    year: int,
    month: int,
    is_edit: bool = True,
) -> None:
    """Вспомогательная функция отрисовки календаря для клиента."""
    today = datetime.date.today()
    max_date = today + datetime.timedelta(days=30)

    start_date = today.strftime("%Y-%m-%d")
    end_date = max_date.strftime("%Y-%m-%d")

    # Получаем даты, где есть хотя бы 1 свободный слот
    available_dates = await db.get_dates_with_available_slots(start_date, end_date)

    calendar_kb = generate_calendar_keyboard(
        year=year,
        month=month,
        available_dates=available_dates,
        is_admin=False,
        mode="user",
    )

    text = (
        "<b>📅 Выберите дату визита:</b>\n\n"
        "🟢 — дни со свободными окошками для записи.\n"
        "<i>Запись доступна на 1 месяц вперед.</i>"
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


# ------------------ Начало записи ------------------


@router.callback_query(F.data == "btn_book")
async def callback_book(
    callback: CallbackQuery, bot: Bot, state: FSMContext
) -> None:
    """Начало процесса бронирования."""
    await state.clear()
    user_id = callback.from_user.id

    # 1. Проверка обязательной подписки на канал (если включена)
    is_subscribed = await check_user_subscription(bot, user_id)
    if not is_subscribed:
        await callback.answer()
        sub_text = (
            "<b>⚠️ Внимание!</b>\n\n"
            "Для записи необходимо подписаться на наш Telegram-канал.\n"
            "После подписки нажмите кнопку «Проверить подписку»."
        )
        if callback.message:
            await callback.message.edit_text(
                text=sub_text,
                reply_markup=subscription_kb(config.CHANNEL_LINK or "https://t.me/"),
            )
        return

    # 2. Проверка: один пользователь может иметь только 1 активную запись
    active_apt = await db.get_active_appointment_by_user(user_id)
    if active_apt:
        await callback.answer()
        text = (
            "<b>⚠️ У вас уже есть активная запись!</b>\n\n"
            f"📅 <b>Дата:</b> {active_apt['date']}\n"
            f"⏰ <b>Время:</b> {active_apt['time']}\n"
            f"👤 <b>Имя:</b> {active_apt['user_name']}\n\n"
            "Вы можете записаться только на один слот одновременно. "
            "Чтобы выбрать другое время, сначала отмените текущую запись."
        )
        if callback.message:
            await callback.message.edit_text(
                text=text,
                reply_markup=my_appointment_kb(active_apt["id"]),
            )
        return

    # 3. Открываем календарь
    await callback.answer()
    today = datetime.date.today()
    await _show_calendar_for_user(callback, today.year, today.month)


@router.callback_query(F.data == "check_subscription")
async def callback_check_subscription(callback: CallbackQuery, bot: Bot) -> None:
    """Повторная проверка подписки на канал."""
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(bot, user_id)

    if is_subscribed:
        await callback.answer("✅ Подписка подтверждена!", show_alert=True)
        today = datetime.date.today()
        await _show_calendar_for_user(callback, today.year, today.month)
    else:
        await callback.answer(
            "❌ Вы еще не подписались на канал. Пожалуйста, подпишитесь и повторите попытку.",
            show_alert=True,
        )


# ------------------ Навигация по календарю ------------------


@router.callback_query(F.data.startswith("cal_nav:user:"))
async def callback_calendar_nav(callback: CallbackQuery) -> None:
    """Переключение месяца в календаре клиента."""
    await callback.answer()
    parts = callback.data.split(":")
    year, month = int(parts[2]), int(parts[3])
    await _show_calendar_for_user(callback, year, month)


@router.callback_query(F.data == "cal_no_slots")
async def callback_no_slots(callback: CallbackQuery) -> None:
    """Нажатие на дату без свободных слотов."""
    await callback.answer(
        "На эту дату нет свободных окошек. Пожалуйста, выберите дату с отметкой 🟢.",
        show_alert=True,
    )


@router.callback_query(F.data == "cal_ignore")
async def callback_ignore(callback: CallbackQuery) -> None:
    """Пустые и неактивные кнопки календаря."""
    await callback.answer()


# ------------------ Выбор даты и слота ------------------


@router.callback_query(F.data.startswith("cal:user:"))
async def callback_select_date(callback: CallbackQuery) -> None:
    """Клиент выбрал дату в календаре."""
    date_str = callback.data.split(":")[2]
    slots = await db.get_available_slots(date_str)

    if not slots:
        await callback.answer(
            "К сожалению, на эту дату все слоты уже заняты.", show_alert=True
        )
        today = datetime.date.today()
        await _show_calendar_for_user(callback, today.year, today.month)
        return

    await callback.answer()
    text = (
        f"<b>📅 Дата:</b> {date_str}\n\n"
        "Выберите удобное время для записи:"
    )
    if callback.message:
        await callback.message.edit_text(
            text=text, reply_markup=slots_kb(slots, date_str)
        )


@router.callback_query(F.data.startswith("slot_pick:"))
async def callback_pick_slot(callback: CallbackQuery, state: FSMContext) -> None:
    """Клиент выбрал конкретный слот времени."""
    parts = callback.data.split(":")
    slot_id = int(parts[1])
    date_str = parts[2]

    slot = await db.get_slot_by_id(slot_id)
    if not slot or slot["is_booked"] == 1:
        await callback.answer(
            "Этот слот только что был занят. Пожалуйста, выберите другое время.",
            show_alert=True,
        )
        slots = await db.get_available_slots(date_str)
        if slots and callback.message:
            await callback.message.edit_text(
                f"<b>📅 Дата:</b> {date_str}\n\nВыберите другое удобное время:",
                reply_markup=slots_kb(slots, date_str),
            )
        else:
            today = datetime.date.today()
            await _show_calendar_for_user(callback, today.year, today.month)
        return

    await callback.answer()
    # Сохраняем выбранный слот в FSM
    await state.update_data(
        slot_id=slot_id,
        date=date_str,
        time=slot["time"],
    )
    await state.set_state(BookingStates.waiting_for_name)

    prompt = (
        f"Вы выбрали: <b>{date_str} в {slot['time']}</b> 💅\n\n"
        "Пожалуйста, напишите ваше <b>имя</b>:"
    )
    if callback.message:
        await callback.message.edit_text(text=prompt, reply_markup=cancel_input_kb())


# ------------------ FSM: Ввод имени и телефона ------------------


@router.message(BookingStates.waiting_for_name)
async def process_name_input(message: Message, state: FSMContext) -> None:
    """Получение имени клиента."""
    name = message.text.strip() if message.text else ""
    if len(name) < 2 or len(name) > 50:
        await message.answer(
            "Пожалуйста, введите корректное имя (от 2 до 50 символов):",
            reply_markup=cancel_input_kb(),
        )
        return

    await state.update_data(user_name=name)
    await state.set_state(BookingStates.waiting_for_phone)

    prompt = (
        f"Приятно познакомиться, <b>{name}</b>!\n\n"
        "Теперь укажите ваш <b>номер телефона</b> для связи.\n"
        "Вы можете нажать кнопку ниже или отправить номер сообщением:"
    )
    await message.answer(text=prompt, reply_markup=phone_request_kb())


@router.message(BookingStates.waiting_for_phone)
async def process_phone_input(message: Message, state: FSMContext) -> None:
    """Получение номера телефона (через контакт или текст)."""
    phone = ""
    if message.contact:
        phone = message.contact.phone_number
    elif message.text:
        # Простая очистка и проверка номера телефона
        raw_phone = message.text.strip()
        digits = re.sub(r"\D", "", raw_phone)
        if len(digits) >= 10:
            phone = raw_phone
        else:
            await message.answer(
                "Пожалуйста, введите корректный номер телефона (например, +79991234567):",
                reply_markup=cancel_input_kb(),
            )
            return

    await state.update_data(phone=phone)
    await state.set_state(BookingStates.waiting_for_confirm)

    data = await state.get_data()
    summary = (
        "<b>📋 Пожалуйста, проверьте данные вашей записи:</b>\n\n"
        "💅 <b>Процедура:</b> Маникюр\n"
        f"📅 <b>Дата:</b> {data['date']}\n"
        f"⏰ <b>Время:</b> {data['time']}\n"
        f"👤 <b>Имя:</b> {data['user_name']}\n"
        f"📞 <b>Телефон:</b> {data['phone']}\n\n"
        "<i>Нажмите «Подтвердить запись», чтобы забронировать окошко.</i>"
    )

    # Удаляем reply-клавиатуру контакта и отправляем inline-подтверждение
    await message.answer(
        "Данные приняты!", reply_markup=remove_reply_kb()
    )
    await message.answer(text=summary, reply_markup=confirm_booking_kb())


@router.callback_query(F.data == "cancel_booking_process")
async def callback_cancel_process(callback: CallbackQuery, state: FSMContext) -> None:
    """Отмена процесса бронирования на любом этапе FSM."""
    await state.clear()
    await callback.answer("Бронирование отменено.")
    if callback.message:
        await callback.message.answer(
            "Бронирование отменено. Вы вернулись в главное меню.",
            reply_markup=main_menu_kb(),
        )


@router.callback_query(BookingStates.waiting_for_confirm, F.data == "confirm_booking")
async def callback_confirm_booking(
    callback: CallbackQuery, bot: Bot, state: FSMContext
) -> None:
    """Подтверждение и фиксация бронирования в базе данных."""
    data = await state.get_data()
    user_id = callback.from_user.id

    slot_id = data.get("slot_id")
    user_name = data.get("user_name")
    phone = data.get("phone")

    if not slot_id or not user_name or not phone:
        await callback.answer("Ошибка данных. Начните запись заново.", show_alert=True)
        await state.clear()
        return

    # Создаем запись атомарно в SQLite
    appointment = await db.create_appointment(
        user_id=user_id,
        user_name=user_name,
        phone=phone,
        slot_id=slot_id,
    )

    await state.clear()

    if not appointment:
        await callback.answer(
            "Не удалось завершить бронирование. Возможно, этот слот уже заняли или у вас уже есть активная запись.",
            show_alert=True,
        )
        if callback.message:
            await callback.message.edit_text(
                "Бронирование не удалось. Вы вернулись в главное меню:",
                reply_markup=main_menu_kb(),
            )
        return

    await callback.answer("🎉 Запись успешно подтверждена!")

    success_text = (
        "<b>🎉 Вы успешно записаны!</b>\n\n"
        "💅 <b>Процедура:</b> Маникюр\n"
        f"📅 <b>Дата:</b> {appointment['date']}\n"
        f"⏰ <b>Время:</b> {appointment['time']}\n"
        f"👤 <b>Имя:</b> {appointment['user_name']}\n"
        f"📞 <b>Телефон:</b> {appointment['phone']}\n\n"
        "Будем рады видеть вас! За 24 часа до визита мы пришлем вам напоминание.\n"
        "Управлять своей записью вы можете в разделе «Моя запись»."
    )
    if callback.message:
        await callback.message.edit_text(
            text=success_text, reply_markup=main_menu_kb()
        )

    # Уведомления и планирование
    await notify_admin_new_booking(bot, appointment)
    await notify_channel_new_booking(bot, appointment)
    schedule_appointment_reminder(bot, appointment)


# ------------------ Раздел «Моя запись» и отмена ------------------


@router.callback_query(F.data == "btn_my_appointment")
async def callback_my_appointment(callback: CallbackQuery) -> None:
    """Просмотр своей активной записи."""
    await callback.answer()
    user_id = callback.from_user.id
    apt = await db.get_active_appointment_by_user(user_id)

    if not apt:
        text = (
            "<b>📋 Моя запись</b>\n\n"
            "У вас пока нет активных записей на маникюр.\n"
            "Желаете выбрать дату и записаться?"
        )
        if callback.message:
            await callback.message.edit_text(
                text=text, reply_markup=main_menu_kb()
            )
        return

    text = (
        "<b>📋 Ваша активная запись:</b>\n\n"
        "💅 <b>Процедура:</b> Маникюр\n"
        f"📅 <b>Дата:</b> {apt['date']}\n"
        f"⏰ <b>Время:</b> {apt['time']}\n"
        f"👤 <b>Имя:</b> {apt['user_name']}\n"
        f"📞 <b>Телефон:</b> {apt['phone']}\n\n"
        "Если ваши планы изменились, пожалуйста, отмените запись заранее, "
        "чтобы освободить слот для других клиентов."
    )
    if callback.message:
        await callback.message.edit_text(
            text=text, reply_markup=my_appointment_kb(apt["id"])
        )


@router.callback_query(F.data.startswith("user_cancel_apt:"))
async def callback_user_cancel_apt(callback: CallbackQuery, bot: Bot) -> None:
    """Отмена записи клиентом."""
    user_id = callback.from_user.id
    apt = await db.cancel_appointment_by_user(user_id)

    if not apt:
        await callback.answer("Активная запись не найдена.", show_alert=True)
        return

    await callback.answer("Запись успешно отменена.", show_alert=True)

    # Удаляем задачу напоминания
    cancel_appointment_reminder(apt["id"])

    # Уведомляем администратора
    await notify_admin_cancellation(bot, apt, by="client")

    text = (
        "<b>✅ Ваша запись успешно отменена.</b>\n\n"
        f"Слот на <b>{apt['date']} в {apt['time']}</b> снова стал доступен для записи.\n"
        "Будем рады видеть вас в другое время!"
    )
    if callback.message:
        await callback.message.edit_text(text=text, reply_markup=main_menu_kb())
