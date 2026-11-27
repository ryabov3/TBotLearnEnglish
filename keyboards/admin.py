# keyboards/admin.py
"""Клавиатуры для роли администратора."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from lexicon import LEXICON


def get_admin_panel_kb(is_founder: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    layout = [2, 2, 2, 2, 2]

    builder.button(text=LEXICON["btn_adm_add_teacher"], callback_data="admin_add_teacher")
    builder.button(text=LEXICON["btn_adm_rem_teacher"], callback_data="admin_rem_teacher")
    builder.button(text=LEXICON["btn_adm_teachers"], callback_data="admtl_0")
    builder.button(text=LEXICON["btn_adm_actions"], callback_data="adm_actl_0")
    builder.button(
        text=LEXICON["btn_adm_broad_student"], callback_data="admin_broad_student"
    )
    builder.button(
        text=LEXICON["btn_adm_broad_teacher"], callback_data="admin_broad_teacher"
    )
    builder.button(text=LEXICON["btn_adm_pm"], callback_data="admin_pml_0")
    builder.button(text=LEXICON["btn_adm_unlink"], callback_data="adm_unl_0")
    builder.button(text=LEXICON["btn_adm_ban"], callback_data="admin_ban")
    builder.button(text=LEXICON["btn_adm_unban"], callback_data="admin_unban")

    if is_founder:
        builder.button(text=LEXICON["btn_adm_add_admin"], callback_data="admin_add_admin")
        builder.button(text=LEXICON["btn_adm_rem_admin"], callback_data="admin_rem_admin")
        layout.append(2)

    builder.button(text=LEXICON["btn_main_menu"], callback_data="s_panel")
    layout.append(1)

    builder.adjust(*layout)
    return builder.as_markup()


def get_cancel_admin_kb(back_cb: str = "admin_back") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_cancel"], callback_data=back_cb)
    return builder.as_markup()


def get_admin_back_kb(
    callback_data: str = "admin_back", text_key: str = "btn_adm_back_panel"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON[text_key], callback_data=callback_data)
    return builder.as_markup()


def get_admin_paginated_list_kb(
    buttons: list[tuple[str, str]],
    page: int,
    total_pages: int,
    page_prefix: str,
    back_cb: str = "admin_back",
    back_text_key: str = "btn_adm_back_panel",
    columns: int = 1,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for text, cb_data in buttons:
        b.button(text=text, callback_data=cb_data)
    b.adjust(columns)

    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text=LEXICON["btn_prev_page"], callback_data=f"{page_prefix}{page - 1}")
    if page < total_pages - 1:
        nav.button(text=LEXICON["btn_next_page"], callback_data=f"{page_prefix}{page + 1}")
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON[back_text_key], callback_data=back_cb)
    b.attach(back)
    return b.as_markup()
