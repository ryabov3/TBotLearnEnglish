# states/states.py
from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    confirm = State() # <-- Добавили шаг подтверждения

class ChangeProfile(StatesGroup):
    first_name = State()
    last_name = State()

class AdminPanel(StatesGroup):
    waiting_for_username_teacher = State()
    waiting_for_username_remove = State()
    waiting_for_username_ban = State()
    waiting_for_username_unban = State()

class TeacherGroup(StatesGroup):
    class_name = State()
    group_name = State()

class TeacherAddStudent(StatesGroup):
    select_group = State()
    waiting_for_username = State()

class TeacherTask(StatesGroup):
    title = State()
    description = State()
    media = State()
    select_groups = State()

class TeacherCheck(StatesGroup):
    waiting_for_grade = State()
    waiting_for_comment = State()

class StudentTask(StatesGroup):
    waiting_for_answer = State()