"""FSM-состояния для панели управления администратора."""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Состояния администратора."""

    waiting_for_slots_input = State()
