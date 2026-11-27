# handlers/student.py
from datetime import date, timedelta

from aiogram import F, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from config.config import ADMINS_ID, FOUNDERS_ID
from database.cache import (
    get_group_tasks_cached,
    get_task_cached,
    get_user_cached,
    invalidate_user_cache,
)
from database.engine import SessionLocal
from database.models import Submission, Task, User
from keyboards.student import (
    get_after_answer_kb,
    get_answer_confirm_kb,
    get_answer_retry_kb,
    get_back_to_student_menu_kb,
    get_cancel_student_kb,
    get_choose_role_kb,
    get_completed_tasks_kb,
    get_exit_task_kb,
    get_profile_kb,
    get_reg_confirm_kb,
    get_student_panel_kb,
    get_submission_details_kb,
    get_topics_kb,
)
from keyboards.teacher import get_teacher_panel_kb
from lexicon import LEXICON
from states.states import ChangeProfile, Registration, StudentTask

student_router = Router()


def get_role_label(role: str) -> str:
    labels = {
        "student": LEXICON["role_student_name"],
        "teacher": LEXICON["role_teacher_name"],
        "admin": LEXICON["role_admin_name"],
        "founder": LEXICON["role_founder_name"],
    }
    return labels.get(role, role)


async def send_role_panel(message: types.Message, role: str, is_edit: bool = False):
    if role in ("teacher", "admin", "founder"):
        markup = get_teacher_panel_kb(
            has_draft=False, show_admin_btn=(role in ("admin", "founder"))
        )
        text = LEXICON["panel_teacher_title"]
    else:
        markup = get_student_panel_kb()
        text = LEXICON["panel_student_title"]

    if is_edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=markup)


# ================= РЕГИСТРАЦИЯ И СТАРТ =================
@student_router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.set_state(None)
    tg_id = message.from_user.id
    username = message.from_user.username or LEXICON["no_username"]

    changed = False
    async with SessionLocal() as session:
        user = await session.get(User, tg_id)
        if user:
            if user.is_banned:
                return await message.answer(LEXICON["user_banned"])

            if tg_id in FOUNDERS_ID and user.role != "founder":
                user.role = "founder"
                changed = True
            elif tg_id in ADMINS_ID and user.role not in ("admin", "founder"):
                user.role = "admin"
                changed = True

            if user.username != username:
                user.username = username
                changed = True

            if changed:
                await session.commit()

            user_role = user.role
            user_class = user.class_name
            user_group = user.group_name
            has_name = bool(user.first_name and user.last_name)
        else:
            user_role = None
            user_class = None
            user_group = None
            has_name = False

    if changed:
        await invalidate_user_cache(
            tg_id,
            user_class,
            user_group,
            invalidate_teachers=(user_role in ("teacher", "admin", "founder")),
        )

    # Пользователь ещё не зарегистрирован (или не завершил ввод имени/фамилии)
    if not has_name:
        if tg_id in FOUNDERS_ID:
            await state.update_data(reg_role="founder")
            await message.answer(LEXICON["reg_welcome_admin"], parse_mode="HTML")
            await state.set_state(Registration.first_name)
        elif tg_id in ADMINS_ID:
            await state.update_data(reg_role="admin")
            await message.answer(LEXICON["reg_welcome_admin"], parse_mode="HTML")
            await state.set_state(Registration.first_name)
        else:
            await message.answer(
                LEXICON["reg_welcome_choose_role"],
                parse_mode="HTML",
                reply_markup=get_choose_role_kb(),
            )
            await state.set_state(Registration.role)
        return

    await send_role_panel(message, user_role, is_edit=False)


@student_router.callback_query(
    Registration.role, F.data.in_(["reg_role_student", "reg_role_teacher"])
)
async def reg_choose_role(callback: types.CallbackQuery, state: FSMContext):
    role = "teacher" if callback.data == "reg_role_teacher" else "student"
    await state.update_data(reg_role=role)
    await callback.message.edit_text(
        LEXICON["reg_role_selected"].format(role_label=get_role_label(role)),
        parse_mode="HTML",
    )
    await state.set_state(Registration.first_name)
    await callback.answer()


@student_router.message(Registration.first_name, F.text)
async def reg_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await message.answer(LEXICON["reg_enter_last_name"], parse_mode="HTML")
    await state.set_state(Registration.last_name)


@student_router.message(Registration.last_name, F.text)
async def reg_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text.strip())
    data = await state.get_data()
    role = data.get("reg_role", "founder" if message.from_user.id in FOUNDERS_ID else ("admin" if message.from_user.id in ADMINS_ID else "student"))

    await message.answer(
        LEXICON["reg_confirm_data"].format(
            role_label=get_role_label(role),
            first_name=data["first_name"],
            last_name=data["last_name"],
        ),
        parse_mode="HTML",
        reply_markup=get_reg_confirm_kb(),
    )
    await state.set_state(Registration.confirm)


@student_router.callback_query(Registration.confirm, F.data == "reg_confirm")
async def reg_confirm_yes(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = callback.from_user.id
    username = callback.from_user.username or LEXICON["no_username"]
    chosen_role = data.get("reg_role", "founder" if tg_id in FOUNDERS_ID else ("admin" if tg_id in ADMINS_ID else "student"))

    async with SessionLocal() as session:
        user = await session.get(User, tg_id)
        if not user:
            user = User(
                id=tg_id,
                username=username,
                first_name=data["first_name"],
                last_name=data["last_name"],
                role=chosen_role,
            )
            session.add(user)
        else:
            user.username = username
            user.first_name = data["first_name"]
            user.last_name = data["last_name"]
            user.role = chosen_role
        await session.commit()
        role = user.role
        c_name, g_name = user.class_name, user.group_name

    await invalidate_user_cache(
        tg_id,
        c_name,
        g_name,
        invalidate_teachers=(role in ("teacher", "admin", "founder")),
    )
    await state.set_state(None)
    await callback.message.edit_text(LEXICON["reg_saved"])
    await send_role_panel(callback.message, role, is_edit=False)


@student_router.callback_query(Registration.confirm, F.data == "reg_edit")
async def reg_confirm_no(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id in FOUNDERS_ID or callback.from_user.id in ADMINS_ID:
        await callback.message.edit_text(
            LEXICON["reg_retry_first_name"], parse_mode="HTML"
        )
        await state.set_state(Registration.first_name)
    else:
        await callback.message.edit_text(
            LEXICON["reg_retry_choose_role"],
            parse_mode="HTML",
            reply_markup=get_choose_role_kb(),
        )
        await state.set_state(Registration.role)


# ================= МЕНЮ И ПРОФИЛЬ =================
@student_router.callback_query(F.data == "s_panel")
async def back_to_student_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    user = await get_user_cached(callback.from_user.id)
    if user and not user.is_banned:
        await send_role_panel(callback.message, user.role, is_edit=True)


@student_router.callback_query(F.data == "s_profile")
async def inline_profile(callback: types.CallbackQuery):
    await show_profile(callback.message, is_callback=True, original_callback=callback)


async def show_profile(
    message: types.Message, is_callback: bool = False, original_callback=None
):
    user_id = message.chat.id if is_callback else message.from_user.id
    user = await get_user_cached(user_id)
    if not user or user.is_banned:
        return

    text = LEXICON["student_profile"].format(
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        role_label=get_role_label(user.role),
        class_name=user.class_name or LEXICON["no_class"],
        group_name=user.group_name or LEXICON["no_group"],
        current_streak=user.current_streak,
        total_completed=user.total_completed,
        max_tasks_per_day=user.max_tasks_per_day,
    )

    markup = get_profile_kb()
    if is_callback:
        await original_callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=markup
        )
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=markup)


@student_router.callback_query(F.data == "s_edit_name")
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        LEXICON["edit_first_name_prompt"],
        parse_mode="HTML",
        reply_markup=get_cancel_student_kb(),
    )
    await state.set_state(ChangeProfile.first_name)


@student_router.message(ChangeProfile.first_name, F.text)
async def edit_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text.strip())
    await message.answer(
        LEXICON["edit_last_name_prompt"],
        parse_mode="HTML",
        reply_markup=get_cancel_student_kb(),
    )
    await state.set_state(ChangeProfile.last_name)


@student_router.message(ChangeProfile.last_name, F.text)
async def edit_last_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        user.first_name = data["first_name"]
        user.last_name = message.text.strip()
        await session.commit()
        role = user.role
        c_name, g_name = user.class_name, user.group_name

    await invalidate_user_cache(
        message.from_user.id,
        c_name,
        g_name,
        invalidate_teachers=(role in ("teacher", "admin", "founder")),
    )
    await state.set_state(None)
    await message.answer(LEXICON["edit_name_success"])
    await send_role_panel(message, role, is_edit=False)


# ================= ВЫПОЛНЕННЫЕ ЗАДАНИЯ =================
@student_router.callback_query(F.data == "s_completed")
async def show_completed_tasks(callback: types.CallbackQuery):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Submission, Task)
            .join(Task, Submission.task_id == Task.id)
            .where(Submission.student_id == callback.from_user.id)
            .order_by(Submission.id.desc())
            .limit(10)
        )
        rows = result.all()

    if not rows:
        return await callback.message.edit_text(
            LEXICON["student_no_completed"],
            reply_markup=get_back_to_student_menu_kb(),
        )

    await callback.message.edit_text(
        LEXICON["student_completed_title"],
        parse_mode="HTML",
        reply_markup=get_completed_tasks_kb(rows),
    )


@student_router.callback_query(F.data.startswith("s_sub_"))
async def show_submission_details(callback: types.CallbackQuery):
    sub_id = int(callback.data.split("_")[2])
    async with SessionLocal() as session:
        result = await session.execute(
            select(Submission, Task)
            .join(Task, Submission.task_id == Task.id)
            .where(Submission.id == sub_id)
        )
        sub, task = result.first()

    grade_str = str(sub.grade) if sub.grade else LEXICON["student_grade_not_checked"]
    comment_str = sub.teacher_comment or LEXICON["no_comment"]

    text = LEXICON["student_submission_details"].format(
        topic=task.topic,
        title=task.title,
        description=task.description,
        grade=grade_str,
        comment=comment_str,
    )
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=get_submission_details_kb()
    )


# ================= ОТОБРАЖЕНИЕ ТЕМ =================
@student_router.callback_query(F.data.in_(["s_tasks_new", "s_tasks_progress"]))
async def show_topics(callback: types.CallbackQuery, state: FSMContext):
    is_progress_tab = callback.data == "s_tasks_progress"

    user = await get_user_cached(callback.from_user.id)
    if not user or not user.class_name:
        return await callback.message.edit_text(
            LEXICON["student_no_group"],
            reply_markup=get_back_to_student_menu_kb(),
        )

    all_tasks = await get_group_tasks_cached(user.class_name, user.group_name)

    async with SessionLocal() as session:
        subs_result = await session.execute(
            select(Submission.task_id).where(Submission.student_id == user.id)
        )
        completed_task_ids = {r[0] for r in subs_result.all()}

    topics = {}
    for t in all_tasks:
        if t.topic not in topics:
            topics[t.topic] = {"total": 0, "completed": 0, "first_uncompleted_id": None}

        topics[t.topic]["total"] += 1
        if t.id in completed_task_ids:
            topics[t.topic]["completed"] += 1
        elif topics[t.topic]["first_uncompleted_id"] is None:
            topics[t.topic]["first_uncompleted_id"] = t.id

    topic_buttons: list[tuple[str, str]] = []
    for topic_name, data in topics.items():
        is_new = data["completed"] == 0
        in_progress = 0 < data["completed"] < data["total"]

        if (is_progress_tab and in_progress) or (not is_progress_tab and is_new):
            progress_text = f"({data['completed']}/{data['total']})"
            btn_data = f"s_do_t_{data['first_uncompleted_id']}"
            topic_buttons.append((f"📂 {topic_name} {progress_text}", btn_data))

    title_text = (
        LEXICON["student_topics_progress_title"]
        if is_progress_tab
        else LEXICON["student_topics_new_title"]
    )
    empty_text = (
        LEXICON["student_topics_progress_empty"]
        if is_progress_tab
        else LEXICON["student_topics_new_empty"]
    )

    if not topic_buttons:
        await callback.message.edit_text(
            empty_text, reply_markup=get_back_to_student_menu_kb()
        )
    else:
        await callback.message.edit_text(
            title_text,
            parse_mode="HTML",
            reply_markup=get_topics_kb(topic_buttons),
        )


# ================= ВЫПОЛНЕНИЕ ЗАДАНИЯ =================
@student_router.callback_query(F.data.startswith("s_do_t_"))
async def start_specific_task(callback: types.CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split("_")[3])

    task = await get_task_cached(task_id)
    if not task:
        return await callback.answer(LEXICON["task_not_found"])

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        LEXICON["student_task_card"].format(
            topic=task.topic, title=task.title, description=task.description
        ),
        parse_mode="HTML",
    )

    if task.media_id:
        await callback.message.answer(LEXICON["teacher_attachment"])
        if task.media_type == "photo":
            await callback.message.answer_photo(task.media_id)
        elif task.media_type == "voice":
            await callback.message.answer_voice(task.media_id)
        elif task.media_type == "video_note":
            await callback.message.answer_video_note(task.media_id)
        elif task.media_type == "video":
            await callback.message.answer_video(task.media_id)
        elif task.media_type == "audio":
            await callback.message.answer_audio(task.media_id)
        elif task.media_type == "document":
            await callback.message.answer_document(task.media_id)

    req_text = LEXICON["req_format_any"]
    if task.expected_answer == "audio":
        req_text = LEXICON["req_format_audio"]
    elif task.expected_answer == "video":
        req_text = LEXICON["req_format_video"]

    await callback.message.answer(
        LEXICON["student_task_instructions"].format(req_text=req_text),
        parse_mode="HTML",
        reply_markup=get_exit_task_kb(),
    )

    await state.update_data(current_task_id=task.id, current_topic=task.topic)
    await state.set_state(StudentTask.waiting_for_answer)


@student_router.message(
    StudentTask.waiting_for_answer, ~(F.voice | F.video_note | F.video | F.audio)
)
async def receive_answer_invalid(message: types.Message):
    await message.answer(LEXICON["student_answer_invalid_media"])


@student_router.message(
    StudentTask.waiting_for_answer, F.voice | F.video_note | F.video | F.audio
)
async def receive_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    task_id = data.get("current_task_id")
    if not task_id:
        return

    task = await get_task_cached(task_id)
    if not task:
        return await message.answer(LEXICON["task_not_found_or_deleted"])

    media_type = (
        "voice"
        if (message.voice or message.audio)
        else ("video_note" if message.video_note else "video")
    )
    media_id = (
        message.voice.file_id
        if message.voice
        else (
            message.audio.file_id
            if message.audio
            else (
                message.video_note.file_id
                if message.video_note
                else message.video.file_id
            )
        )
    )

    if task.expected_answer == "audio" and media_type not in ["voice", "audio"]:
        return await message.answer(
            LEXICON["student_answer_only_audio"], parse_mode="HTML"
        )
    elif task.expected_answer == "video" and media_type not in ["video_note", "video"]:
        return await message.answer(
            LEXICON["student_answer_only_video"], parse_mode="HTML"
        )

    await state.update_data(temp_media_id=media_id, temp_media_type=media_type)
    await message.answer(
        LEXICON["student_answer_confirm"], reply_markup=get_answer_confirm_kb()
    )
    await state.set_state(StudentTask.confirm_answer)


@student_router.callback_query(StudentTask.confirm_answer, F.data == "ans_retry")
async def retry_answer(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(temp_media_id=None, temp_media_type=None)
    await callback.message.edit_text(
        LEXICON["student_answer_retry"], reply_markup=get_answer_retry_kb()
    )
    await state.set_state(StudentTask.waiting_for_answer)


@student_router.callback_query(StudentTask.confirm_answer, F.data == "ans_send")
async def send_answer_to_db(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task_id = data["current_task_id"]
    topic = data["current_topic"]

    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        today = date.today()
        if user.last_task_date == today:
            user.tasks_today += 1
        else:
            if user.last_task_date == today - timedelta(days=1):
                user.current_streak += 1
            else:
                user.current_streak = 1
            user.tasks_today = 1
            user.last_task_date = today

        if user.tasks_today > user.max_tasks_per_day:
            user.max_tasks_per_day = user.tasks_today

        user.total_completed += 1

        new_sub = Submission(
            task_id=task_id,
            student_id=callback.from_user.id,
            media_id=data["temp_media_id"],
            media_type=data["temp_media_type"],
        )
        session.add(new_sub)
        await session.commit()

        user_class, user_group = user.class_name, user.group_name

        subq = select(Submission.task_id).where(Submission.student_id == user.id)
        result = await session.execute(
            select(Task)
            .where(
                Task.class_name == user.class_name,
                Task.group_name == user.group_name,
                Task.topic == topic,
                Task.id.not_in(subq),
            )
            .order_by(Task.id)
            .limit(1)
        )
        next_task = result.scalar_one_or_none()

    await invalidate_user_cache(callback.from_user.id, user_class, user_group)

    try:
        await callback.message.delete()
    except Exception:
        pass

    if next_task:
        await callback.message.answer(
            LEXICON["student_answer_sent_more"],
            reply_markup=get_after_answer_kb(next_task.id),
        )
    else:
        await callback.message.answer(
            LEXICON["student_topic_finished"].format(topic=topic),
            parse_mode="HTML",
            reply_markup=get_after_answer_kb(None),
        )

    await state.set_state(None)
