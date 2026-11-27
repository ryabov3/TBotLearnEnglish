# keyboards/teacher.py
"""Клавиатуры для роли учителя."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from lexicon import LEXICON


def get_teacher_panel_kb(
    has_draft: bool = False, show_admin_btn: bool = False
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    layout: list[int] = []

    if has_draft:
        builder.button(text=LEXICON["btn_t_resume_draft"], callback_data="t_resume_draft")
        layout.append(1)

    builder.button(text=LEXICON["btn_t_new_task"], callback_data="t_new_task")
    builder.button(text=LEXICON["btn_t_del_task"], callback_data="t_del_task_start")
    builder.button(text=LEXICON["btn_t_check_tasks"], callback_data="t_check_tasks_0")
    builder.button(text=LEXICON["btn_t_checked_tasks"], callback_data="t_chkd_pg_0")
    builder.button(text=LEXICON["btn_t_list_classes"], callback_data="t_lc_pg_0")
    builder.button(text=LEXICON["btn_t_stats"], callback_data="t_st_pg_0")
    builder.button(text=LEXICON["btn_t_add_group"], callback_data="t_add_group")
    builder.button(text=LEXICON["btn_t_add_student"], callback_data="t_add_student")
    builder.button(text=LEXICON["btn_t_rem_student"], callback_data="t_rem_student")
    builder.button(text=LEXICON["btn_s_profile"], callback_data="s_profile")
    layout.extend([2, 2, 2, 2, 2])

    if show_admin_btn:
        builder.button(text=LEXICON["btn_open_admin_panel"], callback_data="admin_back")
        layout.append(1)

    builder.adjust(*layout)
    return builder.as_markup()


def get_cancel_teacher_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_cancel"], callback_data="t_menu")
    return builder.as_markup()


def get_cancel_or_back_teacher_kb(back_cb: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if back_cb:
        builder.button(text=LEXICON["btn_back_step"], callback_data=back_cb)
    builder.button(text=LEXICON["btn_cancel"], callback_data="t_menu")
    builder.adjust(2 if back_cb else 1)
    return builder.as_markup()


def get_teacher_back_kb(
    callback_data: str = "t_menu", text_key: str = "btn_back_to_menu"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON[text_key], callback_data=callback_data)
    return builder.as_markup()


def get_paginated_groups_kb(
    groups: list,
    page: int,
    total_pages: int,
    item_prefix: str,
    page_prefix: str,
    item_emoji: str = "📂",
    back_cb: str = "t_menu",
    back_text_key: str = "btn_home_menu",
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for g in groups:
        b.button(
            text=f"{item_emoji} {g.class_name} - {g.group_name}",
            callback_data=f"{item_prefix}{g.id}",
        )
    b.adjust(2)

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


def get_teacher_groups_select_kb(
    groups: list, item_prefix: str, back_cb: str = "t_menu"
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in groups:
        builder.button(
            text=f"{g.class_name} - {g.group_name}",
            callback_data=f"{item_prefix}{g.id}",
        )
    builder.adjust(2)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON["btn_back"], callback_data=back_cb)
    builder.attach(back)
    return builder.as_markup()


def get_rem_students_page_kb(
    students: list, group_id: int, page: int, total_pages: int
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in students:
        b.button(
            text=f"👤 {s.first_name} {s.last_name}",
            callback_data=f"rem_u_{s.id}_{group_id}",
        )
    b.adjust(1)

    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(
            text=LEXICON["btn_prev_page"], callback_data=f"rem_pg_{group_id}_{page - 1}"
        )
    if page < total_pages - 1:
        nav.button(
            text=LEXICON["btn_next_page"], callback_data=f"rem_pg_{group_id}_{page + 1}"
        )
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON["btn_t_back_groups"], callback_data="t_rem_student")
    b.attach(back)
    return b.as_markup()


def get_task_media_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_t_skip_media"], callback_data="skip_media")
    builder.button(text=LEXICON["btn_back_step"], callback_data="t_back_to_desc")
    builder.button(text=LEXICON["btn_cancel"], callback_data="t_menu")
    builder.adjust(1, 2)
    return builder.as_markup()


def get_answer_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_t_ans_audio"], callback_data="ans_type_audio")
    builder.button(text=LEXICON["btn_t_ans_video"], callback_data="ans_type_video")
    builder.button(text=LEXICON["btn_t_ans_any"], callback_data="ans_type_any")
    builder.button(text=LEXICON["btn_back_step"], callback_data="t_back_to_desc")
    builder.button(text=LEXICON["btn_cancel"], callback_data="t_menu")
    builder.adjust(2, 1, 2)
    return builder.as_markup()


def get_add_more_tasks_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_t_add_more"], callback_data="t_add_more_yes")
    builder.button(text=LEXICON["btn_t_remake_last"], callback_data="t_remake_current")
    builder.button(text=LEXICON["btn_t_preview"], callback_data="t_preview_topic")
    builder.button(text=LEXICON["btn_t_select_groups"], callback_data="t_add_more_no")
    builder.button(text=LEXICON["btn_t_postpone"], callback_data="t_menu")
    builder.adjust(2, 2, 1)
    return builder.as_markup()


def get_select_groups_for_task_kb(
    groups: list, selected_ids: list[int]
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in groups:
        mark = "✅ " if g.id in selected_ids else ""
        builder.button(
            text=f"{mark}{g.class_name} - {g.group_name}",
            callback_data=f"tg_group_{g.id}",
        )
    builder.adjust(2)

    actions = InlineKeyboardBuilder()
    actions.button(text=LEXICON["btn_t_publish_topic"], callback_data="confirm_task")
    actions.button(text=LEXICON["btn_t_go_back"], callback_data="t_back_to_ask_more")
    actions.button(text=LEXICON["btn_cancel"], callback_data="t_menu")
    actions.adjust(1, 2)
    builder.attach(actions)
    return builder.as_markup()


def get_del_topics_page_kb(
    current_topics: list[str], page: int, total_pages: int, per_page: int
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for i, topic in enumerate(current_topics):
        idx = page * per_page + i
        display_name = topic if len(topic) < 30 else topic[:30] + "..."
        b.button(text=f"🗑 {display_name}", callback_data=f"t_del_t_{idx}")
    b.adjust(1)

    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text=LEXICON["btn_prev_page"], callback_data=f"t_del_pg_{page - 1}")
    if page < total_pages - 1:
        nav.button(text=LEXICON["btn_next_page"], callback_data=f"t_del_pg_{page + 1}")
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON["btn_back_to_menu"], callback_data="t_menu")
    b.attach(back)
    return b.as_markup()


def get_del_topic_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text=LEXICON["btn_t_confirm_delete"], callback_data="t_del_task_yes")
    b.button(text=LEXICON["btn_cancel"], callback_data="t_del_task_start")
    b.adjust(2)
    return b.as_markup()


def get_check_tasks_list_kb(
    tasks: list, callback_fn, back_cb: str
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for t in tasks:
        builder.button(text=f"📌 {t.topic} | {t.title}", callback_data=callback_fn(t))
    builder.adjust(1)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON["btn_back"], callback_data=back_cb)
    builder.attach(back)
    return builder.as_markup()


def get_check_students_list_kb(rows: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for sub, student in rows:
        name = (
            f"{student.first_name} {student.last_name} "
            f"(@{student.username or LEXICON['no_username'].lower()})"
        )
        builder.button(text=name, callback_data=f"t_chk_s_{sub.id}")
    builder.adjust(1)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON["btn_home_menu"], callback_data="t_menu")
    builder.attach(back)
    return builder.as_markup()


def get_after_grade_kb(task_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_t_back_task"], callback_data=f"t_chk_t_{task_id}")
    builder.button(text=LEXICON["btn_home_menu"], callback_data="t_menu")
    builder.adjust(2)
    return builder.as_markup()


def get_checked_students_page_kb(
    students: list,
    submissions: dict,
    group_id: int,
    task_id: int,
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for s in students:
        sub = submissions.get(s.id)
        if sub and sub.grade is not None:
            mark = "✅"
            cb_data = f"t_chkd_s_{sub.id}_{group_id}_{task_id}"
        else:
            mark = "❌"
            cb_data = "t_chkd_ns"

        name = f"{s.first_name or ''} {s.last_name or ''}".strip() or s.username or str(s.id)
        b.button(text=f"{mark} {name}", callback_data=cb_data)
    b.adjust(1)

    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(
            text=LEXICON["btn_prev_page"],
            callback_data=f"t_chkd_t_{group_id}_{task_id}_{page - 1}",
        )
    if page < total_pages - 1:
        nav.button(
            text=LEXICON["btn_next_page"],
            callback_data=f"t_chkd_t_{group_id}_{task_id}_{page + 1}",
        )
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON["btn_t_back_tasks"], callback_data=f"t_chkd_g_{group_id}")
    b.attach(back)
    return b.as_markup()


def get_group_stats_kb(group_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=LEXICON["btn_t_students_list"], callback_data=f"t_st_l_{group_id}")
    builder.button(text=LEXICON["btn_t_back_to_groups"], callback_data="t_st_pg_0")
    builder.adjust(2)
    return builder.as_markup()


def get_stats_students_list_kb(students: list, group_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in students:
        builder.button(
            text=f"👤 {s.first_name} {s.last_name}",
            callback_data=f"t_st_u_{s.id}_{group_id}",
        )
    builder.adjust(2)

    back = InlineKeyboardBuilder()
    back.button(text=LEXICON["btn_back"], callback_data=f"t_st_g_{group_id}")
    builder.attach(back)
    return builder.as_markup()
