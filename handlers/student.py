# handlers/student.py
"""Основной роутер Telegram-бота: регистрация, запуск Web App, сдача и прослушивание медиа-ответов."""

from datetime import date, timedelta

from aiogram import F, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from config.config import ADMINS_ID, FOUNDERS_ID
from database.cache import (
    get_task_cached,
    get_user_cached,
    invalidate_user_cache,
)
from database.engine import SessionLocal
from database.models import Submission, Task, User
from filters import ValidNameFilter, normalize_name
from keyboards.student import (
    get_after_answer_kb,
    get_answer_confirm_kb,
    get_choose_role_kb,
    get_exit_task_kb,
    get_open_webapp_kb,
    get_reg_confirm_kb,
)
from lexicon import LEXICON
from states.states import Registration, StudentTask

student_router = Router()


def get_role_label(role: str) -> str:
    labels = {
        "student": LEXICON["role_student_name"],
        "teacher": LEXICON["role_teacher_name"],
        "admin": LEXICON["role_admin_name"],
        "founder": LEXICON["role_founder_name"],
    }
    return labels.get(role, role)


async def send_webapp_home(message: types.Message, first_name: str, role: str):
    markup = get_open_webapp_kb()
    role_label = get_role_label(role)
    if markup:
        await message.answer(
            LEXICON["welcome_back_webapp"].format(
                first_name=first_name, role_label=role_label
            ),
            parse_mode="HTML",
            reply_markup=markup,
        )
    else:
        await message.answer(
            LEXICON["welcome_back_no_url"].format(
                first_name=first_name, role_label=role_label
            ),
            parse_mode="HTML",
        )


async def _send_task_to_student(message: types.Message, task, state: FSMContext):
    await message.answer(
        LEXICON["student_task_card"].format(
            topic=task.topic, title=task.title, description=task.description
        ),
        parse_mode="HTML",
    )

    if task.media_id:
        await message.answer(LEXICON["teacher_attachment"])
        if task.media_type == "photo":
            await message.answer_photo(task.media_id)
        elif task.media_type == "voice":
            await message.answer_voice(task.media_id)
        elif task.media_type == "video_note":
            await message.answer_video_note(task.media_id)
        elif task.media_type == "video":
            await message.answer_video(task.media_id)
        elif task.media_type == "audio":
            await message.answer_audio(task.media_id)
        elif task.media_type == "document":
            await message.answer_document(task.media_id)

    req_text = LEXICON["req_format_any"]
    if task.expected_answer == "audio":
        req_text = LEXICON["req_format_audio"]
    elif task.expected_answer == "video":
        req_text = LEXICON["req_format_video"]

    await message.answer(
        LEXICON["student_task_instructions"].format(req_text=req_text),
        parse_mode="HTML",
        reply_markup=get_exit_task_kb(),
    )
    await state.update_data(current_task_id=task.id, current_topic=task.topic)
    await state.set_state(StudentTask.waiting_for_answer)


async def _send_submission_for_review(message: types.Message, sub_id: int, role: str):
    if role not in ("teacher", "admin", "founder"):
        return await message.answer(LEXICON["no_teacher_rights"])

    async with SessionLocal() as session:
        res = await session.execute(
            select(Submission, User, Task)
            .join(User, Submission.student_id == User.id)
            .join(Task, Submission.task_id == Task.id)
            .where(Submission.id == sub_id)
        )
        row = res.first()

    if not row:
        return await message.answer(LEXICON["review_sub_not_found"])

    sub, student, task = row
    student_name = (
        f"{student.first_name or ''} {student.last_name or ''}".strip()
        or student.username
        or str(student.id)
    )
    await message.answer(
        LEXICON["review_sub_header"].format(
            student_name=student_name,
            username=student.username or LEXICON["no_username"].lower(),
            topic=task.topic,
            title=task.title,
        ),
        parse_mode="HTML",
        reply_markup=get_open_webapp_kb(),
    )

    if sub.media_type == "voice":
        await message.answer_voice(sub.media_id)
    elif sub.media_type == "video_note":
        await message.answer_video_note(sub.media_id)
    elif sub.media_type == "video":
        await message.answer_video(sub.media_id)


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
            first_name = user.first_name
            has_name = bool(user.first_name and user.last_name)
        else:
            user_role = None
            user_class = None
            user_group = None
            first_name = None
            has_name = False

    if changed:
        await invalidate_user_cache(
            tg_id,
            user_class,
            user_group,
            invalidate_teachers=(user_role in ("teacher", "admin", "founder")),
        )

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

    # Поддержка deep-link из Mini App: /start task_<id> и /start review_<sub_id>
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 2:
        arg = parts[1].strip()
        if arg.startswith("task_") and arg[5:].isdigit():
            task = await get_task_cached(int(arg[5:]))
            if task:
                await _send_task_to_student(message, task, state)
                return
            await message.answer(LEXICON["task_not_found_or_deleted"])
            return
        if arg.startswith("review_") and arg[7:].isdigit():
            await _send_submission_for_review(message, int(arg[7:]), user_role)
            return

    await send_webapp_home(message, first_name or "", user_role)


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


@student_router.message(Registration.first_name, ValidNameFilter())
async def reg_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=normalize_name(message.text))
    await message.answer(LEXICON["reg_enter_last_name"], parse_mode="HTML")
    await state.set_state(Registration.last_name)


@student_router.message(Registration.first_name)
async def reg_first_name_invalid(message: types.Message):
    await message.answer(LEXICON["invalid_first_name"], parse_mode="HTML")


@student_router.message(Registration.last_name, ValidNameFilter())
async def reg_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=normalize_name(message.text))
    data = await state.get_data()
    role = data.get(
        "reg_role",
        "founder"
        if message.from_user.id in FOUNDERS_ID
        else ("admin" if message.from_user.id in ADMINS_ID else "student"),
    )

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


@student_router.message(Registration.last_name)
async def reg_last_name_invalid(message: types.Message):
    await message.answer(LEXICON["invalid_last_name"], parse_mode="HTML")


@student_router.callback_query(Registration.confirm, F.data == "reg_confirm")
async def reg_confirm_yes(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    tg_id = callback.from_user.id
    username = callback.from_user.username or LEXICON["no_username"]
    chosen_role = data.get(
        "reg_role",
        "founder"
        if tg_id in FOUNDERS_ID
        else ("admin" if tg_id in ADMINS_ID else "student"),
    )

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
    await send_webapp_home(callback.message, data["first_name"], role)


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


# ================= СДАЧА МЕДИА-ОТВЕТОВ =================
@student_router.callback_query(F.data == "s_cancel_task")
async def cancel_task(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)
    await callback.message.edit_text(
        LEXICON["student_task_cancelled"], reply_markup=get_open_webapp_kb()
    )


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

    await _send_task_to_student(callback.message, task, state)


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
        LEXICON["student_answer_retry"], reply_markup=get_exit_task_kb()
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
