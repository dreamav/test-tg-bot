"""FSM-состояния для процесса бронирования клиентом."""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния бронирования слота."""

    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_confirm = State()
