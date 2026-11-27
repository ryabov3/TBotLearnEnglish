# handlers/teacher.py
from collections import defaultdict

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import delete, select

from database.cache import (
    get_group_cached,
    get_group_stats_cached,
    get_group_students_cached,
    get_group_tasks_cached,
    get_task_cached,
    get_teacher_groups_cached,
    get_user_cached,
    invalidate_group_stats_cache,
    invalidate_group_students_cache,
    invalidate_group_tasks_cache,
    invalidate_tasks_cache,
    invalidate_teacher_groups_cache,
    invalidate_user_cache,
    set_group_stats_cached,
)
from database.engine import SessionLocal
from database.models import StudyGroup, Submission, Task, User
from filters import IsTeacherFilter
from keyboards.teacher import (
    get_add_more_tasks_kb,
    get_after_grade_kb,
    get_answer_type_kb,
    get_cancel_or_back_teacher_kb,
    get_cancel_teacher_kb,
    get_check_students_list_kb,
    get_check_tasks_list_kb,
    get_checked_students_page_kb,
    get_del_topic_confirm_kb,
    get_del_topics_page_kb,
    get_group_stats_kb,
    get_paginated_groups_kb,
    get_rem_students_page_kb,
    get_select_groups_for_task_kb,
    get_stats_students_list_kb,
    get_task_media_kb,
    get_teacher_back_kb,
    get_teacher_groups_select_kb,
    get_teacher_panel_kb,
)
from lexicon import LEXICON
from states.states import (
    TeacherAddStudent,
    TeacherCheck,
    TeacherDeleteTask,
    TeacherGroup,
    TeacherTask,
)

teacher_router = Router()
teacher_router.message.filter(IsTeacherFilter())
teacher_router.callback_query.filter(IsTeacherFilter())


@teacher_router.callback_query(F.data == "t_menu")
async def teacher_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.set_state(None)

    user = await get_user_cached(callback.from_user.id)
    show_admin_btn = bool(user and user.role in ("admin", "founder"))
    has_draft = bool(data.get("tasks_list") or data.get("topic"))
    await callback.message.edit_text(
        LEXICON["panel_teacher_title"],
        parse_mode="HTML",
        reply_markup=get_teacher_panel_kb(
            has_draft=has_draft, show_admin_btn=show_admin_btn
        ),
    )


# ================= 0. СПИСОК КЛАССОВ =================
@teacher_router.callback_query(F.data.startswith("t_lc_pg_"))
async def list_classes_pages(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    per_page = 6

    groups = await get_teacher_groups_cached(callback.from_user.id)

    if not groups:
        return await callback.message.edit_text(
            LEXICON["teacher_no_classes"], reply_markup=get_teacher_back_kb()
        )

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page * per_page : (page + 1) * per_page]

    await callback.message.edit_text(
        LEXICON["teacher_choose_class_pg"].format(
            page=page + 1, total_pages=total_pages
        ),
        reply_markup=get_paginated_groups_kb(
            current_groups,
            page,
            total_pages,
            item_prefix="t_lc_g_",
            page_prefix="t_lc_pg_",
            item_emoji="📋",
        ),
    )


@teacher_router.callback_query(F.data.startswith("t_lc_g_"))
async def list_class_students(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])

    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["group_not_found"], show_alert=True)
    students = await get_group_students_cached(group.class_name, group.group_name)

    back_kb = get_teacher_back_kb(callback_data="t_lc_pg_0", text_key="btn_back")
    if not students:
        return await callback.message.edit_text(
            LEXICON["teacher_class_empty"].format(
                class_name=group.class_name, group_name=group.group_name
            ),
            parse_mode="HTML",
            reply_markup=back_kb,
        )

    text = LEXICON["teacher_class_list_header"].format(
        class_name=group.class_name, group_name=group.group_name
    )
    for i, s in enumerate(students, 1):
        uname = f"@{s.username}" if s.username else LEXICON["no_username"].lower()
        text += (
            f"{i}. {group.class_name}-{group.group_name} - "
            f"{s.first_name} {s.last_name} ({uname})\n"
        )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_kb)


# ================= 1. СОЗДАНИЕ ГРУППЫ =================
@teacher_router.callback_query(F.data == "t_add_group")
async def start_add_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON["teacher_enter_class_name"], reply_markup=get_cancel_teacher_kb()
    )
    await state.set_state(TeacherGroup.class_name)


@teacher_router.message(TeacherGroup.class_name, F.text)
async def process_class_name(message: types.Message, state: FSMContext):
    await state.update_data(class_name=message.text.strip())
    await message.answer(
        LEXICON["teacher_enter_group_name"], reply_markup=get_cancel_teacher_kb()
    )
    await state.set_state(TeacherGroup.group_name)


@teacher_router.message(TeacherGroup.group_name, F.text)
async def process_group_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        new_group = StudyGroup(
            teacher_id=message.from_user.id,
            class_name=data["class_name"],
            group_name=message.text.strip(),
        )
        session.add(new_group)
        await session.commit()

    await invalidate_teacher_groups_cache(message.from_user.id)

    await message.answer(
        LEXICON["teacher_group_saved"], reply_markup=get_teacher_back_kb()
    )
    await state.set_state(None)


# ================= 2. ДОБАВЛЕНИЕ УЧЕНИКА В ГРУППУ =================
@teacher_router.callback_query(F.data == "t_add_student")
async def start_add_student(callback: types.CallbackQuery, state: FSMContext):
    groups = await get_teacher_groups_cached(callback.from_user.id)

    if not groups:
        return await callback.message.edit_text(
            LEXICON["teacher_no_groups_create"], reply_markup=get_teacher_back_kb()
        )

    await callback.message.edit_text(
        LEXICON["teacher_choose_group_add_student"],
        reply_markup=get_teacher_groups_select_kb(groups, item_prefix="sel_group_"),
    )
    await state.set_state(TeacherAddStudent.select_group)


@teacher_router.callback_query(
    TeacherAddStudent.select_group, F.data.startswith("sel_group_")
)
async def add_student_group_selected(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[2])
    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["group_not_found"], show_alert=True)
    await state.update_data(class_name=group.class_name, group_name=group.group_name)
    await callback.message.edit_text(
        LEXICON["teacher_group_selected_username"].format(
            class_name=group.class_name, group_name=group.group_name
        ),
        reply_markup=get_cancel_teacher_kb(),
    )
    await state.set_state(TeacherAddStudent.waiting_for_username)


@teacher_router.message(TeacherAddStudent.waiting_for_username, F.text)
async def add_student_username(message: types.Message, state: FSMContext):
    username = message.text.replace("@", "").strip()
    data = await state.get_data()
    old_class = None
    old_group = None
    student_id = None
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        student = result.scalar_one_or_none()

        if not student:
            await message.answer(
                LEXICON["teacher_student_not_found"].format(username=username),
                reply_markup=get_teacher_back_kb(),
            )
        else:
            old_class, old_group = student.class_name, student.group_name
            student_id = student.id
            student.class_name = data["class_name"]
            student.group_name = data["group_name"]
            await session.commit()
            await message.answer(
                LEXICON["teacher_student_added"].format(
                    username=username,
                    class_name=data["class_name"],
                    group_name=data["group_name"],
                ),
                reply_markup=get_teacher_back_kb(),
            )

    if student_id is not None:
        await invalidate_user_cache(student_id, data["class_name"], data["group_name"])
        if old_class and old_group and (
            old_class != data["class_name"] or old_group != data["group_name"]
        ):
            await invalidate_group_students_cache(old_class, old_group)

    await state.set_state(None)


# ================= 2.1 УДАЛЕНИЕ УЧЕНИКА =================
@teacher_router.callback_query(F.data == "t_rem_student")
async def rem_student_start(callback: types.CallbackQuery, state: FSMContext):
    groups = await get_teacher_groups_cached(callback.from_user.id)
    if not groups:
        return await callback.message.edit_text(
            LEXICON["teacher_no_groups_short"], reply_markup=get_teacher_back_kb()
        )
    await callback.message.edit_text(
        LEXICON["teacher_choose_group_rem_student"],
        reply_markup=get_teacher_groups_select_kb(groups, item_prefix="rem_g_"),
    )


@teacher_router.callback_query(F.data.startswith("rem_g_"))
async def rem_student_group_selected(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[2])
    await show_rem_students_page(callback, group_id, 0)


@teacher_router.callback_query(F.data.startswith("rem_pg_"))
async def rem_student_page(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    group_id = int(parts[2])
    page = int(parts[3])
    await show_rem_students_page(callback, group_id, page)


async def show_rem_students_page(callback: types.CallbackQuery, group_id: int, page: int):
    per_page = 5
    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["group_not_found"], show_alert=True)
    students = await get_group_students_cached(group.class_name, group.group_name)

    if not students:
        return await callback.message.edit_text(
            LEXICON["teacher_group_no_students"],
            reply_markup=get_teacher_back_kb(
                callback_data="t_rem_student", text_key="btn_back"
            ),
        )

    total_pages = max(1, (len(students) + per_page - 1) // per_page)
    current_students = students[page * per_page : (page + 1) * per_page]

    await callback.message.edit_text(
        LEXICON["teacher_rem_student_pg"].format(
            class_name=group.class_name,
            group_name=group.group_name,
            page=page + 1,
            total_pages=total_pages,
        ),
        parse_mode="HTML",
        reply_markup=get_rem_students_page_kb(
            current_students, group_id, page, total_pages
        ),
    )


@teacher_router.callback_query(F.data.startswith("rem_u_"))
async def rem_student_confirm(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    student_id = int(parts[2])
    group_id = int(parts[3])

    old_class, old_group = None, None
    async with SessionLocal() as session:
        student = await session.get(User, student_id)
        if student:
            old_class, old_group = student.class_name, student.group_name
            student.class_name = None
            student.group_name = None
            await session.commit()

    await invalidate_user_cache(student_id, old_class, old_group)

    await callback.answer(LEXICON["teacher_student_removed_alert"], show_alert=True)
    await show_rem_students_page(callback, group_id, 0)


# ================= 3. СОЗДАНИЕ ЗАДАНИЙ =================
@teacher_router.callback_query(F.data == "t_new_task")
async def start_new_task(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(tasks_list=[])
    await callback.message.edit_text(
        LEXICON["teacher_enter_topic"],
        parse_mode="HTML",
        reply_markup=get_cancel_teacher_kb(),
    )
    await state.set_state(TeacherTask.topic)


@teacher_router.callback_query(F.data == "t_resume_draft")
async def resume_task_draft(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("tasks_list"):
        await ask_add_more(callback.message, state)
    elif data.get("topic"):
        await callback.message.edit_text(
            LEXICON["teacher_enter_title"].format(topic=data["topic"]),
            parse_mode="HTML",
            reply_markup=get_cancel_or_back_teacher_kb("t_back_to_topic"),
        )
        await state.set_state(TeacherTask.title)
    else:
        await start_new_task(callback, state)


@teacher_router.callback_query(F.data == "t_back_to_topic")
async def back_to_topic(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(tasks_list=[])
    await callback.message.edit_text(
        LEXICON["teacher_enter_topic"],
        parse_mode="HTML",
        reply_markup=get_cancel_teacher_kb(),
    )
    await state.set_state(TeacherTask.topic)


@teacher_router.message(TeacherTask.topic, F.text)
async def task_topic(message: types.Message, state: FSMContext):
    if len(message.text) > 250:
        return await message.answer(
            LEXICON["teacher_topic_too_long"],
            reply_markup=get_cancel_or_back_teacher_kb("t_back_to_topic"),
        )

    await state.update_data(topic=message.text)
    await message.answer(
        LEXICON["teacher_enter_first_title"].format(topic=message.text),
        parse_mode="HTML",
        reply_markup=get_cancel_or_back_teacher_kb("t_back_to_topic"),
    )
    await state.set_state(TeacherTask.title)


@teacher_router.callback_query(F.data == "t_back_to_ask_more")
async def back_to_ask_more(callback: types.CallbackQuery, state: FSMContext):
    await ask_add_more(callback.message, state)


@teacher_router.callback_query(F.data == "t_back_to_title")
async def back_to_title(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tasks_list = data.get("tasks_list", [])
    back_cb = "t_back_to_ask_more" if len(tasks_list) > 0 else "t_back_to_topic"
    await callback.message.edit_text(
        LEXICON["teacher_enter_title"].format(topic=data.get("topic", "")),
        parse_mode="HTML",
        reply_markup=get_cancel_or_back_teacher_kb(back_cb),
    )
    await state.set_state(TeacherTask.title)


@teacher_router.message(TeacherTask.title, F.text)
async def task_title(message: types.Message, state: FSMContext):
    if len(message.text) > 250:
        return await message.answer(
            LEXICON["teacher_title_too_long"],
            reply_markup=get_cancel_or_back_teacher_kb("t_back_to_title"),
        )

    await state.update_data(current_title=message.text)
    await message.answer(
        LEXICON["teacher_enter_desc"],
        reply_markup=get_cancel_or_back_teacher_kb("t_back_to_title"),
    )
    await state.set_state(TeacherTask.description)


@teacher_router.callback_query(F.data == "t_back_to_desc")
async def back_to_desc(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        LEXICON["teacher_enter_desc_with_title"].format(
            title=data.get("current_title", "")
        ),
        parse_mode="HTML",
        reply_markup=get_cancel_or_back_teacher_kb("t_back_to_title"),
    )
    await state.set_state(TeacherTask.description)


@teacher_router.message(TeacherTask.description, F.text)
async def task_desc(message: types.Message, state: FSMContext):
    await state.update_data(current_description=message.text)
    await message.answer(
        LEXICON["teacher_send_media"], reply_markup=get_task_media_kb()
    )
    await state.set_state(TeacherTask.media)


@teacher_router.callback_query(TeacherTask.media, F.data == "skip_media")
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(temp_media_id=None, temp_media_type=None)
    await ask_answer_type(callback.message, state)
    await callback.answer()


@teacher_router.message(
    TeacherTask.media,
    F.photo | F.video | F.audio | F.voice | F.video_note | F.document,
)
async def task_media(message: types.Message, state: FSMContext):
    media_id = None
    media_type = None

    if message.photo:
        media_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video:
        media_id, media_type = message.video.file_id, "video"
    elif message.audio:
        media_id, media_type = message.audio.file_id, "audio"
    elif message.voice:
        media_id, media_type = message.voice.file_id, "voice"
    elif message.video_note:
        media_id, media_type = message.video_note.file_id, "video_note"
    elif message.document:
        media_id, media_type = message.document.file_id, "document"

    await state.update_data(temp_media_id=media_id, temp_media_type=media_type)
    await ask_answer_type(message, state)


async def ask_answer_type(message_or_callback: types.Message, state: FSMContext):
    text = LEXICON["teacher_choose_answer_type"]
    markup = get_answer_type_kb()
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, reply_markup=markup)
    else:
        await message_or_callback.edit_text(text, reply_markup=markup)
    await state.set_state(TeacherTask.answer_type)


@teacher_router.callback_query(
    TeacherTask.answer_type, F.data.startswith("ans_type_")
)
async def process_answer_type(callback: types.CallbackQuery, state: FSMContext):
    ans_type = callback.data.split("_")[2]
    data = await state.get_data()
    tasks_list = data.get("tasks_list", [])

    tasks_list.append(
        {
            "title": data["current_title"],
            "description": data["current_description"],
            "media_id": data.get("temp_media_id"),
            "media_type": data.get("temp_media_type"),
            "expected_answer": ans_type,
        }
    )

    await state.update_data(tasks_list=tasks_list)
    await ask_add_more(callback.message, state)
    await callback.answer()


async def ask_add_more(
    message_or_callback: types.Message, state: FSMContext, is_after_preview: bool = False
):
    data = await state.get_data()
    tasks_list = data.get("tasks_list", [])

    if is_after_preview:
        text = LEXICON["teacher_after_preview"].format(
            topic=data["topic"], count=len(tasks_list)
        )
    else:
        current_task = tasks_list[-1]
        text = LEXICON["teacher_task_added"].format(
            title=current_task["title"], topic=data["topic"]
        )

    await state.set_state(TeacherTask.add_more)
    markup = get_add_more_tasks_kb()
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message_or_callback.edit_text(text, parse_mode="HTML", reply_markup=markup)


@teacher_router.callback_query(F.data == "t_remake_current")
async def remake_current(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tasks_list = data.get("tasks_list", [])
    if tasks_list:
        tasks_list.pop()
    await state.update_data(tasks_list=tasks_list)

    back_cb = "t_back_to_ask_more" if len(tasks_list) > 0 else "t_back_to_topic"
    await callback.message.edit_text(
        LEXICON["teacher_enter_title_again"].format(topic=data.get("topic", "")),
        parse_mode="HTML",
        reply_markup=get_cancel_or_back_teacher_kb(back_cb),
    )
    await state.set_state(TeacherTask.title)


@teacher_router.callback_query(F.data == "t_preview_topic")
async def preview_topic(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tasks_list = data.get("tasks_list", [])
    topic = data.get("topic", "Без темы")

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        LEXICON["teacher_preview_header"].format(topic=topic), parse_mode="HTML"
    )

    for i, t in enumerate(tasks_list, 1):
        req_text = LEXICON["req_format_any"]
        if t["expected_answer"] == "audio":
            req_text = LEXICON["req_format_audio"]
        elif t["expected_answer"] == "video":
            req_text = LEXICON["req_format_video"]

        text = LEXICON["teacher_preview_item"].format(
            topic=topic,
            index=i,
            title=t["title"],
            description=t["description"],
            req_text=req_text,
        )
        await callback.message.answer(text, parse_mode="HTML")

        if t["media_id"]:
            await callback.message.answer(LEXICON["teacher_attachment"])
            if t["media_type"] == "photo":
                await callback.message.answer_photo(t["media_id"])
            elif t["media_type"] == "video":
                await callback.message.answer_video(t["media_id"])
            elif t["media_type"] == "audio":
                await callback.message.answer_audio(t["media_id"])
            elif t["media_type"] == "voice":
                await callback.message.answer_voice(t["media_id"])
            elif t["media_type"] == "video_note":
                await callback.message.answer_video_note(t["media_id"])
            elif t["media_type"] == "document":
                await callback.message.answer_document(t["media_id"])

    await ask_add_more(callback.message, state, is_after_preview=True)
    await callback.answer()


@teacher_router.callback_query(F.data == "t_add_more_yes")
async def add_more_tasks_yes(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await callback.message.edit_text(
        LEXICON["teacher_enter_next_title"].format(topic=data["topic"]),
        parse_mode="HTML",
        reply_markup=get_cancel_or_back_teacher_kb("t_back_to_ask_more"),
    )
    await state.set_state(TeacherTask.title)


@teacher_router.callback_query(F.data == "t_add_more_no")
async def add_more_tasks_no(callback: types.CallbackQuery, state: FSMContext):
    await ask_for_groups(callback.message, state, callback.from_user.id)
    await callback.answer()


async def ask_for_groups(message: types.Message, state: FSMContext, teacher_id: int):
    data = await state.get_data()
    selected = data.get("selected_group_ids", [])

    groups = await get_teacher_groups_cached(teacher_id)

    if not groups:
        await state.set_state(None)
        return await message.edit_text(
            LEXICON["teacher_no_groups_panel"], reply_markup=get_teacher_back_kb()
        )

    text = LEXICON["teacher_select_groups_send"].format(
        topic=data["topic"], count=len(data["tasks_list"])
    )
    await message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_select_groups_for_task_kb(groups, selected),
    )
    await state.set_state(TeacherTask.select_groups)


@teacher_router.callback_query(
    TeacherTask.select_groups, F.data.startswith("tg_group_")
)
async def toggle_group(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get("selected_group_ids", [])

    if group_id in selected:
        selected.remove(group_id)
    else:
        selected.append(group_id)

    await state.update_data(selected_group_ids=selected)
    await ask_for_groups(callback.message, state, callback.from_user.id)
    await callback.answer()


@teacher_router.callback_query(TeacherTask.select_groups, F.data == "confirm_task")
async def confirm_task(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get("selected_group_ids", [])
    if not selected_ids:
        return await callback.answer(
            LEXICON["teacher_select_at_least_one_group"], show_alert=True
        )

    affected_groups: set[tuple[str, str]] = set()
    async with SessionLocal() as session:
        for gid in selected_ids:
            group = await session.get(StudyGroup, gid)
            if not group:
                continue
            affected_groups.add((group.class_name, group.group_name))
            for t_data in data["tasks_list"]:
                new_task = Task(
                    teacher_id=callback.from_user.id,
                    topic=data["topic"],
                    title=t_data["title"],
                    description=t_data["description"],
                    media_id=t_data["media_id"],
                    media_type=t_data["media_type"],
                    class_name=group.class_name,
                    group_name=group.group_name,
                    expected_answer=t_data.get("expected_answer", "any"),
                )
                session.add(new_task)
        await session.commit()

    for c_name, g_name in affected_groups:
        await invalidate_group_tasks_cache(c_name, g_name)
        await invalidate_group_stats_cache(callback.from_user.id, c_name, g_name)

    await state.clear()
    await callback.message.edit_text(
        LEXICON["teacher_topic_published"], reply_markup=get_teacher_back_kb()
    )


# ================= УДАЛЕНИЕ ЗАДАНИЯ =================
@teacher_router.callback_query(F.data == "t_del_task_start")
async def del_task_start(callback: types.CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Task.topic)
            .where(Task.teacher_id == callback.from_user.id)
            .distinct()
        )
        topics = result.scalars().all()

    if not topics:
        return await callback.message.edit_text(
            LEXICON["teacher_no_topics_to_delete"], reply_markup=get_teacher_back_kb()
        )

    await state.update_data(del_topics=topics)
    await state.set_state(TeacherDeleteTask.selecting_topic)
    await show_del_task_page(callback, 0, topics)


@teacher_router.callback_query(
    TeacherDeleteTask.selecting_topic, F.data.startswith("t_del_pg_")
)
async def del_task_page(callback: types.CallbackQuery, state: FSMContext):
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    topics = data.get("del_topics", [])
    await show_del_task_page(callback, page, topics)


async def show_del_task_page(callback: types.CallbackQuery, page: int, topics: list):
    per_page = 5
    total_pages = max(1, (len(topics) + per_page - 1) // per_page)
    current_topics = topics[page * per_page : (page + 1) * per_page]

    await callback.message.edit_text(
        LEXICON["teacher_del_topic_pg"].format(page=page + 1, total_pages=total_pages),
        parse_mode="HTML",
        reply_markup=get_del_topics_page_kb(current_topics, page, total_pages, per_page),
    )


@teacher_router.callback_query(
    TeacherDeleteTask.selecting_topic, F.data.startswith("t_del_t_")
)
async def del_task_confirm(callback: types.CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[-1])
    data = await state.get_data()
    topics = data.get("del_topics", [])

    if idx >= len(topics):
        return await callback.answer(
            LEXICON["teacher_del_topic_not_found"], show_alert=True
        )

    topic_to_delete = topics[idx]
    await state.update_data(topic_to_delete=topic_to_delete)

    await callback.message.edit_text(
        LEXICON["teacher_del_topic_confirm"].format(topic=topic_to_delete),
        parse_mode="HTML",
        reply_markup=get_del_topic_confirm_kb(),
    )


@teacher_router.callback_query(
    TeacherDeleteTask.selecting_topic, F.data == "t_del_task_yes"
)
async def del_task_execute(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    topic_to_delete = data.get("topic_to_delete")

    task_ids: list[int] = []
    affected_groups: set[tuple[str, str]] = set()
    if topic_to_delete:
        async with SessionLocal() as session:
            tasks_res = await session.execute(
                select(Task.id, Task.class_name, Task.group_name).where(
                    Task.teacher_id == callback.from_user.id,
                    Task.topic == topic_to_delete,
                )
            )
            rows = tasks_res.all()
            task_ids = [row[0] for row in rows]
            affected_groups = {(row[1], row[2]) for row in rows}

            if task_ids:
                await session.execute(
                    delete(Submission).where(Submission.task_id.in_(task_ids))
                )
                await session.execute(delete(Task).where(Task.id.in_(task_ids)))
                await session.commit()

    if task_ids:
        await invalidate_tasks_cache(task_ids)
        for c_name, g_name in affected_groups:
            await invalidate_group_tasks_cache(c_name, g_name)
            await invalidate_group_stats_cache(callback.from_user.id, c_name, g_name)

    await state.set_state(None)
    await callback.message.edit_text(
        LEXICON["teacher_del_topic_done"].format(topic=topic_to_delete),
        parse_mode="HTML",
        reply_markup=get_teacher_back_kb(),
    )


# ================= 4. ПРОВЕРКА ЗАДАНИЙ =================
@teacher_router.callback_query(F.data.startswith("t_check_tasks_"))
async def check_tasks_groups(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    per_page = 6

    groups = await get_teacher_groups_cached(callback.from_user.id)

    if not groups:
        return await callback.message.edit_text(
            LEXICON["teacher_no_groups"], reply_markup=get_teacher_back_kb()
        )

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page * per_page : (page + 1) * per_page]

    await callback.message.edit_text(
        LEXICON["teacher_check_groups_pg"].format(
            page=page + 1, total_pages=total_pages
        ),
        reply_markup=get_paginated_groups_kb(
            current_groups,
            page,
            total_pages,
            item_prefix="t_chk_g_",
            page_prefix="t_check_tasks_",
            item_emoji="📂",
        ),
    )


@teacher_router.callback_query(F.data.startswith("t_chk_g_"))
async def check_tasks_in_group(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["group_not_found"], show_alert=True)

    async with SessionLocal() as session:
        result = await session.execute(
            select(Task)
            .join(Submission, Submission.task_id == Task.id)
            .where(
                Task.class_name == group.class_name,
                Task.group_name == group.group_name,
                Task.teacher_id == callback.from_user.id,
                Submission.grade == None,
            )
            .distinct()
            .order_by(Task.topic, Task.id)
        )
        tasks = result.scalars().all()

    if not tasks:
        return await callback.message.edit_text(
            LEXICON["teacher_no_tasks_to_check"],
            reply_markup=get_teacher_back_kb(
                callback_data="t_check_tasks_0", text_key="btn_t_back_to_groups"
            ),
        )

    await callback.message.edit_text(
        LEXICON["teacher_check_select_task"].format(
            class_name=group.class_name, group_name=group.group_name
        ),
        parse_mode="HTML",
        reply_markup=get_check_tasks_list_kb(
            tasks, callback_fn=lambda t: f"t_chk_t_{t.id}", back_cb="t_check_tasks_0"
        ),
    )


@teacher_router.callback_query(F.data.startswith("t_chk_t_"))
async def check_tasks_students(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[-1])
    task = await get_task_cached(task_id)
    if not task:
        return await callback.answer(LEXICON["task_not_found"], show_alert=True)

    async with SessionLocal() as session:
        result = await session.execute(
            select(Submission, User)
            .join(User, Submission.student_id == User.id)
            .where(Submission.task_id == task_id, Submission.grade == None)
        )
        rows = result.all()

    if not rows:
        return await callback.message.edit_text(
            LEXICON["teacher_all_checked"],
            reply_markup=get_teacher_back_kb(
                callback_data="t_check_tasks_0", text_key="btn_back"
            ),
        )

    caption = LEXICON["teacher_check_task_caption"].format(
        topic=task.topic, title=task.title, description=task.description
    )
    markup = get_check_students_list_kb(rows)

    try:
        await callback.message.delete()
    except Exception:
        pass

    if task.media_id:
        if task.media_type == "photo":
            await callback.message.answer_photo(
                task.media_id, caption=caption, parse_mode="HTML", reply_markup=markup
            )
        elif task.media_type == "video":
            await callback.message.answer_video(
                task.media_id, caption=caption, parse_mode="HTML", reply_markup=markup
            )
        elif task.media_type == "voice":
            await callback.message.answer_voice(
                task.media_id, caption=caption, parse_mode="HTML", reply_markup=markup
            )
        elif task.media_type == "audio":
            await callback.message.answer_audio(
                task.media_id, caption=caption, parse_mode="HTML", reply_markup=markup
            )
        elif task.media_type == "document":
            await callback.message.answer_document(
                task.media_id, caption=caption, parse_mode="HTML", reply_markup=markup
            )
        elif task.media_type == "video_note":
            await callback.message.answer(
                caption, parse_mode="HTML", reply_markup=markup
            )
            await callback.message.answer_video_note(task.media_id)
    else:
        await callback.message.answer(caption, parse_mode="HTML", reply_markup=markup)


@teacher_router.callback_query(F.data.startswith("t_chk_s_"))
async def check_tasks_evaluate(callback: types.CallbackQuery, state: FSMContext):
    sub_id = int(callback.data.split("_")[-1])
    async with SessionLocal() as session:
        result = await session.execute(
            select(Submission, User, Task)
            .join(User, Submission.student_id == User.id)
            .join(Task, Submission.task_id == Task.id)
            .where(Submission.id == sub_id)
        )
        row = result.first()
        if not row:
            return await callback.answer(LEXICON["teacher_sub_not_found"])
        sub, student, task = row

    try:
        await callback.message.delete()
    except Exception:
        pass

    text = LEXICON["teacher_student_answer_header"].format(
        first_name=student.first_name,
        last_name=student.last_name,
        username=student.username or LEXICON["no_username"].lower(),
    )
    await callback.message.answer(text, parse_mode="HTML")

    if sub.media_type == "voice":
        await callback.message.answer_voice(sub.media_id)
    elif sub.media_type == "video_note":
        await callback.message.answer_video_note(sub.media_id)
    elif sub.media_type == "video":
        await callback.message.answer_video(sub.media_id)

    await callback.message.answer(
        LEXICON["teacher_enter_grade"], reply_markup=get_cancel_teacher_kb()
    )
    await state.update_data(sub_id=sub.id, task_id=task.id)
    await state.set_state(TeacherCheck.waiting_for_grade)


@teacher_router.message(
    TeacherCheck.waiting_for_grade, F.text.in_(["1", "2", "3", "4", "5"])
)
async def process_grade(message: types.Message, state: FSMContext):
    await state.update_data(grade=int(message.text))
    await message.answer(
        LEXICON["teacher_enter_comment"], reply_markup=get_cancel_teacher_kb()
    )
    await state.set_state(TeacherCheck.waiting_for_comment)


@teacher_router.message(TeacherCheck.waiting_for_grade)
async def process_grade_invalid(message: types.Message):
    await message.answer(LEXICON["teacher_invalid_grade"])


@teacher_router.message(TeacherCheck.waiting_for_comment, F.text)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        sub = await session.get(Submission, data["sub_id"])
        sub.grade = data["grade"]
        sub.teacher_comment = message.text
        task_id = sub.task_id
        await session.commit()

    task = await get_task_cached(task_id)
    if task:
        await invalidate_group_stats_cache(
            task.teacher_id, task.class_name, task.group_name
        )

    await state.set_state(None)
    await message.answer(
        LEXICON["teacher_grade_saved"], reply_markup=get_after_grade_kb(task_id)
    )


# ================= 4.1. ПРОВЕРЕННЫЕ ЗАДАНИЯ =================
@teacher_router.callback_query(F.data.startswith("t_chkd_pg_"))
async def checked_tasks_groups(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    per_page = 6

    groups = await get_teacher_groups_cached(callback.from_user.id)

    if not groups:
        return await callback.message.edit_text(
            LEXICON["teacher_no_groups"], reply_markup=get_teacher_back_kb()
        )

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page * per_page : (page + 1) * per_page]

    await callback.message.edit_text(
        LEXICON["teacher_checked_groups_pg"].format(
            page=page + 1, total_pages=total_pages
        ),
        parse_mode="HTML",
        reply_markup=get_paginated_groups_kb(
            current_groups,
            page,
            total_pages,
            item_prefix="t_chkd_g_",
            page_prefix="t_chkd_pg_",
            item_emoji="📂",
        ),
    )


@teacher_router.callback_query(F.data.startswith("t_chkd_g_"))
async def checked_tasks_in_group(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["group_not_found"], show_alert=True)

    tasks = sorted(
        await get_group_tasks_cached(
            group.class_name, group.group_name, teacher_id=callback.from_user.id
        ),
        key=lambda t: (t.topic, t.id),
    )

    if not tasks:
        return await callback.message.edit_text(
            LEXICON["teacher_checked_no_tasks"].format(
                class_name=group.class_name, group_name=group.group_name
            ),
            parse_mode="HTML",
            reply_markup=get_teacher_back_kb(
                callback_data="t_chkd_pg_0", text_key="btn_t_back_to_groups"
            ),
        )

    await callback.message.edit_text(
        LEXICON["teacher_checked_select_task"].format(
            class_name=group.class_name, group_name=group.group_name
        ),
        parse_mode="HTML",
        reply_markup=get_check_tasks_list_kb(
            tasks,
            callback_fn=lambda t: f"t_chkd_t_{group_id}_{t.id}_0",
            back_cb="t_chkd_pg_0",
        ),
    )


@teacher_router.callback_query(F.data.startswith("t_chkd_t_"))
async def checked_tasks_students(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    group_id = int(parts[3])
    task_id = int(parts[4])
    page = int(parts[5])
    per_page = 5

    task = await get_task_cached(task_id)
    if not task:
        return await callback.answer(LEXICON["task_not_found"], show_alert=True)

    students = await get_group_students_cached(task.class_name, task.group_name)

    async with SessionLocal() as session:
        subs_res = await session.execute(
            select(Submission).where(Submission.task_id == task_id)
        )
        submissions = {s.student_id: s for s in subs_res.scalars().all()}

    if not students:
        return await callback.message.edit_text(
            LEXICON["teacher_group_no_students"],
            reply_markup=get_teacher_back_kb(
                callback_data=f"t_chkd_g_{group_id}", text_key="btn_back"
            ),
        )

    total_pages = max(1, (len(students) + per_page - 1) // per_page)
    current_students = students[page * per_page : (page + 1) * per_page]

    await callback.message.edit_text(
        LEXICON["teacher_checked_students_pg"].format(
            title=task.title, page=page + 1, total_pages=total_pages
        ),
        parse_mode="HTML",
        reply_markup=get_checked_students_page_kb(
            current_students, submissions, group_id, task_id, page, total_pages
        ),
    )


@teacher_router.callback_query(F.data == "t_chkd_ns")
async def checked_tasks_not_submitted(callback: types.CallbackQuery):
    await callback.answer(LEXICON["teacher_checked_not_submitted"], show_alert=True)


@teacher_router.callback_query(F.data.startswith("t_chkd_s_"))
async def checked_tasks_submission(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    sub_id = int(parts[3])
    group_id = int(parts[4])
    task_id = int(parts[5])

    async with SessionLocal() as session:
        result = await session.execute(
            select(Submission, Task)
            .join(Task, Submission.task_id == Task.id)
            .where(Submission.id == sub_id)
        )
        sub, task = result.first()

    text = LEXICON["teacher_checked_sub_details"].format(
        topic=task.topic,
        title=task.title,
        description=task.description,
        grade=sub.grade,
        comment=sub.teacher_comment or LEXICON["no_comment"],
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_teacher_back_kb(
            callback_data=f"t_chkd_t_{group_id}_{task_id}_0",
            text_key="btn_t_back_students",
        ),
    )


# ================= 5. СТАТИСТИКА =================
@teacher_router.callback_query(F.data.startswith("t_st_pg_"))
async def stats_groups_list(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    per_page = 6

    groups = await get_teacher_groups_cached(callback.from_user.id)

    if not groups:
        return await callback.message.edit_text(
            LEXICON["teacher_no_groups"], reply_markup=get_teacher_back_kb()
        )

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page * per_page : (page + 1) * per_page]

    await callback.message.edit_text(
        LEXICON["teacher_stats_groups_pg"].format(
            page=page + 1, total_pages=total_pages
        ),
        reply_markup=get_paginated_groups_kb(
            current_groups,
            page,
            total_pages,
            item_prefix="t_st_g_",
            page_prefix="t_st_pg_",
            item_emoji="📊",
        ),
    )


@teacher_router.callback_query(F.data.startswith("t_st_g_"))
async def stats_group_details(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["group_not_found"], show_alert=True)

    text = await get_group_stats_cached(
        callback.from_user.id, group.class_name, group.group_name
    )

    if text is None:
        tasks = await get_group_tasks_cached(
            group.class_name, group.group_name, teacher_id=callback.from_user.id
        )
        grades_by_task: dict[int, list[int]] = defaultdict(list)

        if tasks:
            task_ids = [t.id for t in tasks]
            async with SessionLocal() as session:
                sub_res = await session.execute(
                    select(Submission.task_id, Submission.grade).where(
                        Submission.task_id.in_(task_ids),
                        Submission.grade != None,
                    )
                )
                for tid, grade in sub_res.all():
                    grades_by_task[tid].append(grade)

        text = LEXICON["teacher_stats_group_header"].format(
            class_name=group.class_name, group_name=group.group_name
        )
        total_grades = []

        for t in tasks:
            grades = grades_by_task.get(t.id, [])
            if grades:
                avg = sum(grades) / len(grades)
                total_grades.extend(grades)
                text += LEXICON["teacher_stats_task_avg"].format(
                    topic=t.topic, title=t.title, avg=avg
                )
            else:
                text += LEXICON["teacher_stats_task_empty"].format(
                    topic=t.topic, title=t.title
                )

        if total_grades:
            overall_avg = sum(total_grades) / len(total_grades)
            text += LEXICON["teacher_stats_overall_avg"].format(avg=overall_avg)
        else:
            text += LEXICON["teacher_stats_overall_empty"]

        await set_group_stats_cached(
            callback.from_user.id, group.class_name, group.group_name, text
        )

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=get_group_stats_kb(group_id)
    )


@teacher_router.callback_query(F.data.startswith("t_st_l_"))
async def stats_student_list(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["group_not_found"], show_alert=True)

    students = await get_group_students_cached(group.class_name, group.group_name)

    if not students:
        return await callback.message.edit_text(
            LEXICON["teacher_group_no_students"],
            reply_markup=get_teacher_back_kb(
                callback_data=f"t_st_g_{group_id}", text_key="btn_back"
            ),
        )

    await callback.message.edit_text(
        LEXICON["teacher_stats_students_header"].format(
            class_name=group.class_name, group_name=group.group_name
        ),
        parse_mode="HTML",
        reply_markup=get_stats_students_list_kb(students, group_id),
    )


@teacher_router.callback_query(F.data.startswith("t_st_u_"))
async def stats_student_details(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    student_id = int(parts[3])
    group_id = int(parts[4])

    student = await get_user_cached(student_id)
    group = await get_group_cached(group_id)
    if not student or not group:
        return await callback.answer(
            LEXICON["teacher_stats_data_not_found"], show_alert=True
        )

    tasks = await get_group_tasks_cached(
        group.class_name, group.group_name, teacher_id=callback.from_user.id
    )

    text = LEXICON["teacher_stats_student_header"].format(
        first_name=student.first_name,
        last_name=student.last_name,
        class_name=group.class_name,
        group_name=group.group_name,
    )

    if not tasks:
        text += LEXICON["teacher_stats_no_tasks"]
    else:
        task_ids = [t.id for t in tasks]
        async with SessionLocal() as session:
            sub_res = await session.execute(
                select(Submission).where(
                    Submission.task_id.in_(task_ids),
                    Submission.student_id == student.id,
                )
            )
            subs_by_task = {s.task_id: s for s in sub_res.scalars().all()}

        for t in tasks:
            sub = subs_by_task.get(t.id)
            if not sub:
                text += LEXICON["teacher_stats_item_not_done"].format(
                    topic=t.topic, title=t.title
                )
            elif sub.grade is None:
                text += LEXICON["teacher_stats_item_pending"].format(
                    topic=t.topic, title=t.title
                )
            else:
                text += LEXICON["teacher_stats_item_graded"].format(
                    topic=t.topic, title=t.title, grade=sub.grade
                )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_teacher_back_kb(
            callback_data=f"t_st_l_{group_id}", text_key="btn_t_back_students"
        ),
    )
