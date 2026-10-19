"""Хэндлеры главного меню, прайсов и портфолио."""

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from keyboards.user_kb import main_menu_kb, portfolio_kb, prices_kb

router = Router(name="menu_router")

PINTEREST_URL = "https://ru.pinterest.com/crystalwithluv/_created/"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Команда /start — приветствие и главное меню."""
    await state.clear()
    welcome_text = (
        f"Здравствуйте, <b>{message.from_user.first_name}</b>! 💅\n\n"
        "Рада приветствовать вас в онлайн-записи к мастеру маникюра!\n"
        "Здесь вы можете посмотреть прайс-лист, работы в портфолио, "
        "а также выбрать удобную дату и время для визита.\n\n"
        "Пожалуйста, выберите интересующий раздел:"
    )
    await message.answer(
        text=welcome_text,
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "btn_to_main_menu")
async def callback_to_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в главное меню бота."""
    await state.clear()
    await callback.answer()
    menu_text = (
        "<b>Главное меню:</b>\n\n"
        "Выберите нужное действие с помощью кнопок ниже:"
    )
    if callback.message:
        await callback.message.edit_text(
            text=menu_text,
            reply_markup=main_menu_kb(),
        )


@router.callback_query(F.data == "btn_prices")
async def callback_prices(callback: CallbackQuery) -> None:
    """
    Раздел «Прайсы».
    Отправляет HTML-сообщение без использования FSM:
    Френч — 1000₽
    Квадрат — 500₽
    """
    await callback.answer()
    prices_text = (
        "<b>💅 Прайс-лист:</b>\n\n"
        "• Френч — 1000₽\n"
        "• Квадрат — 500₽"
    )
    if callback.message:
        await callback.message.edit_text(
            text=prices_text,
            reply_markup=prices_kb(),
        )


@router.callback_query(F.data == "btn_portfolio")
async def callback_portfolio(callback: CallbackQuery) -> None:
    """
    Раздел «Портфолио».
    Отправляет сообщение со ссылкой на Pinterest.
    """
    await callback.answer()
    portfolio_text = (
        "<b>🎨 Портфолио работ</b>\n\n"
        "Посмотреть фотографии выполненных работ и выбрать идею для следующего маникюра "
        "вы можете по кнопке ниже:"
    )
    if callback.message:
        await callback.message.edit_text(
            text=portfolio_text,
            reply_markup=portfolio_kb(PINTEREST_URL),
        )
