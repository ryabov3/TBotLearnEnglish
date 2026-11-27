# keyboards/student.py
"""Клавиатуры Telegram-бота (регистрация, запуск Web App и сдача медиа-ответов)."""

from aiogram.types import InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

import config.config as config
from lexicon import LEXICON


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


def get_open_webapp_kb() -> InlineKeyboardMarkup | None:
    if not config.WEBAPP_URL:
        return None
    builder = InlineKeyboardBuilder()
    builder.button(
        text=LEXICON["btn_open_webapp"],
        web_app=WebAppInfo(url=config.WEBAPP_URL),
    )
    builder.adjust(1)
    return builder.as_markup()


def get_exit_task_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_cancel_task"], callback_data="s_cancel_task")
    return builder.as_markup()


def get_answer_confirm_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_s_send_answer"], callback_data="ans_send")
    builder.button(text=LEXICON["btn_s_retry_answer"], callback_data="ans_retry")
    builder.button(text=LEXICON["btn_s_cancel_task"], callback_data="s_cancel_task")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_after_answer_kb(next_task_id: int | None) -> InlineKeyboardMarkup | None:
    builder = InlineKeyboardBuilder()
    layout: list[int] = []
    if next_task_id is not None:
        builder.button(
            text=LEXICON["btn_s_continue_topic"],
            callback_data=f"s_do_t_{next_task_id}",
        )
        layout.append(1)
    if config.WEBAPP_URL:
        builder.button(
            text=LEXICON["btn_open_webapp"],
            web_app=WebAppInfo(url=config.WEBAPP_URL),
        )
        layout.append(1)
    if not layout:
        return None
    builder.adjust(*layout)
    return builder.as_markup()
