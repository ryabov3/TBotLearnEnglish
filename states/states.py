# states/states.py
from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    confirm = State()

class ChangeProfile(StatesGroup):
    first_name = State()
    last_name = State()

class AdminPanel(StatesGroup):
    waiting_for_username_teacher = State()
    waiting_for_username_remove = State()
    waiting_for_username_ban = State()
    waiting_for_username_unban = State()
    waiting_for_broadcast_text = State() 
    waiting_for_username_actions = State() 

class TeacherGroup(StatesGroup):
    class_name = State()
    group_name = State()

class TeacherAddStudent(StatesGroup):
    select_group = State()
    waiting_for_username = State()

class TeacherRemoveStudent(StatesGroup):
    select_group = State()
    select_student = State()

class TeacherTask(StatesGroup):
    topic = State()
    title = State() 
    description = State()
    media = State()
    answer_type = State()
    add_more = State() 
    select_groups = State()

class TeacherDeleteTask(StatesGroup):
    selecting_topic = State() # Новое состояние для удаления темы

class TeacherCheck(StatesGroup):
    waiting_for_grade = State()
    waiting_for_comment = State()

class StudentTask(StatesGroup):
    waiting_for_answer = State()
    confirm_answer = State()