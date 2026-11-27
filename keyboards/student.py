# keyboards/student.py
"""Клавиатуры для регистрации и роли ученика."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from lexicon import LEXICON


def get_cancel_student_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_cancel"], callback_data="s_panel")
    return builder.as_markup()


def get_back_to_student_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_back_to_menu"], callback_data="s_panel")
    return builder.as_markup()


def get_choose_role_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_role_student"], callback_data="reg_role_student")
    builder.button(text=LEXICON["btn_role_teacher"], callback_data="reg_role_teacher")
    builder.adjust(2)
    return builder.as_markup()


def get_reg_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_reg_confirm"], callback_data="reg_confirm")
    builder.button(text=LEXICON["btn_reg_edit"], callback_data="reg_edit")
    builder.adjust(2)
    return builder.as_markup()


def get_student_panel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_new_tasks"], callback_data="s_tasks_new")
    builder.button(text=LEXICON["btn_s_progress"], callback_data="s_tasks_progress")
    builder.button(text=LEXICON["btn_s_completed"], callback_data="s_completed")
    builder.button(text=LEXICON["btn_s_profile"], callback_data="s_profile")
    builder.adjust(2)
    return builder.as_markup()


def get_profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_edit_name"], callback_data="s_edit_name")
    builder.button(text=LEXICON["btn_back"], callback_data="s_panel")
    builder.adjust(2)
    return builder.as_markup()


def get_completed_tasks_kb(rows: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sub, task in rows:
        grade_str = (
            LEXICON["student_grade_label"].format(grade=sub.grade)
            if sub.grade
            else LEXICON["student_grade_pending"]
        )
        builder.button(
            text=f"📝 {task.topic} | {task.title} ({grade_str})",
            callback_data=f"s_sub_{sub.id}",
        )
    builder.button(text=LEXICON["btn_back_to_menu"], callback_data="s_panel")
    builder.adjust(1)
    return builder.as_markup()


def get_submission_details_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_back_list"], callback_data="s_completed")
    builder.button(text=LEXICON["btn_home_menu"], callback_data="s_panel")
    builder.adjust(2)
    return builder.as_markup()


def get_topics_kb(topic_buttons: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, cb_data in topic_buttons:
        builder.button(text=text, callback_data=cb_data)
    builder.button(text=LEXICON["btn_back_to_menu"], callback_data="s_panel")
    builder.adjust(1)
    return builder.as_markup()


def get_exit_task_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_exit_saved"], callback_data="s_panel")
    return builder.as_markup()


def get_answer_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_send_answer"], callback_data="ans_send")
    builder.button(text=LEXICON["btn_s_retry_answer"], callback_data="ans_retry")
    builder.button(text=LEXICON["btn_s_exit_menu"], callback_data="s_panel")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_answer_retry_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_exit_menu"], callback_data="s_panel")
    return builder.as_markup()


def get_after_answer_kb(next_task_id: int | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if next_task_id is not None:
        builder.button(
            text=LEXICON["btn_s_continue_topic"],
            callback_data=f"s_do_t_{next_task_id}",
        )
        builder.button(text=LEXICON["btn_s_pause_menu"], callback_data="s_panel")
        builder.adjust(2)
    else:
        builder.button(text=LEXICON["btn_s_return_menu"], callback_data="s_panel")
        builder.adjust(1)
    return builder.as_markup()
