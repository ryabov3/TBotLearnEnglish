# states/states.py
from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    role = State()
    first_name = State()
    last_name = State()
    confirm = State()


class StudentTask(StatesGroup):
    waiting_for_answer = State()
    confirm_answer = State()