# handlers/student.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from datetime import date, timedelta

from config import ADMIN_ID
from database.engine import SessionLocal
from database.models import User, Task, Submission
from states.states import StudentTask, Registration, ChangeProfile

student_router = Router()


def get_cancel_s():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="s_panel")
    return builder.as_markup()


async def send_role_panel(message: types.Message, role: str, is_edit: bool = False):
    builder = InlineKeyboardBuilder()
    if role in ["teacher", "admin"]:
        builder.button(text="📝 Создать задание", callback_data="t_new_task")
        builder.button(text="✅ Проверить ответы", callback_data="t_check_tasks_0")
        builder.button(
            text="📊 Статистика", callback_data="t_st_pg_0"
        )  # <-- НОВАЯ КНОПКА
        builder.button(text="➕ Создать группу", callback_data="t_add_group")
        builder.button(text="👤 Добавить ученика", callback_data="t_add_student")
        builder.adjust(1)
        text = "👨‍🏫 <b>Панель Учителя</b>\nВыберите действие:"
    else:
        builder.button(text="📝 Новые задания", callback_data="s_tasks")
        builder.button(text="✅ Выполненные задания", callback_data="s_completed")
        builder.button(text="👤 Мой профиль", callback_data="s_profile")
        builder.adjust(1)
        text = "🎓 <b>Панель Ученика</b>\nЧто хочешь сделать?"

    if is_edit:
        await message.edit_text(
            text, parse_mode="HTML", reply_markup=builder.as_markup()
        )
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())


# ================= РЕГИСТРАЦИЯ И СТАРТ =================
@student_router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        username = message.from_user.username or "Без_юзернейма"

        if not user:
            role = "admin" if message.from_user.id == ADMIN_ID else "student"
            user = User(id=message.from_user.id, username=username, role=role)
            session.add(user)
            await session.commit()

        if user.is_banned:
            return await message.answer("❌ Вы заблокированы администратором.")

        user.username = username
        await session.commit()

        if not user.first_name or not user.last_name:
            await message.answer(
                "👋 Привет! Для начала работы нам нужно познакомиться.\n\nВведите ваше <b>Имя</b>:",
                parse_mode="HTML",
            )
            await state.set_state(Registration.first_name)
            return

        await send_role_panel(message, user.role, is_edit=False)


@student_router.message(Registration.first_name, F.text)
async def reg_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer(
        "Отлично! Теперь введите вашу <b>Фамилию</b>:", parse_mode="HTML"
    )
    await state.set_state(Registration.last_name)


@student_router.message(Registration.last_name, F.text)
async def reg_last_name(message: types.Message, state: FSMContext):
    await state.update_data(last_name=message.text)
    data = await state.get_data()

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Всё верно", callback_data="reg_confirm")
    builder.button(text="🔄 Изменить", callback_data="reg_edit")
    builder.adjust(1)

    await message.answer(
        f"Ваши данные:\nИмя: <b>{data['first_name']}</b>\nФамилия: <b>{data['last_name']}</b>\n\nВсё верно?",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
    )
    await state.set_state(Registration.confirm)


@student_router.callback_query(Registration.confirm, F.data == "reg_confirm")
async def reg_confirm_yes(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        user.first_name = data["first_name"]
        user.last_name = data["last_name"]
        await session.commit()
        role = user.role

    await state.clear()
    await callback.message.edit_text("✅ Отлично! Данные сохранены.")
    await send_role_panel(callback.message, role, is_edit=False)


@student_router.callback_query(Registration.confirm, F.data == "reg_edit")
async def reg_confirm_no(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Давай попробуем снова. Введите ваше <b>Имя</b>:", parse_mode="HTML"
    )
    await state.set_state(Registration.first_name)


# ================= МЕНЮ И ПРОФИЛЬ =================
@student_router.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        if user and not user.is_banned:
            if not user.first_name or not user.last_name:
                await message.answer(
                    "Пожалуйста, сначала введите свое <b>Имя</b>:", parse_mode="HTML"
                )
                await state.set_state(Registration.first_name)
                return
            await send_role_panel(message, user.role, is_edit=False)


@student_router.callback_query(F.data == "s_panel")
async def back_to_student_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        if user and not user.is_banned:
            await send_role_panel(callback.message, user.role, is_edit=True)


@student_router.message(Command("profile"))
async def cmd_profile(message: types.Message, state: FSMContext):
    await state.clear()
    await show_profile(message)


@student_router.callback_query(F.data == "s_profile")
async def inline_profile(callback: types.CallbackQuery):
    await show_profile(callback.message, is_callback=True, original_callback=callback)


async def show_profile(
    message: types.Message, is_callback=False, original_callback=None
):
    async with SessionLocal() as session:
        user = await session.get(
            User, message.chat.id if is_callback else message.from_user.id
        )
        if not user or user.is_banned:
            return

        g = user.group_name if user.group_name else "Нет группы"
        c = user.class_name if user.class_name else "Нет класса"

        text = (
            f"👤 <b>Профиль:</b> {user.first_name} {user.last_name} (@{user.username})\n"
            f"🎓 <b>Роль:</b> {user.role}\n"
            f"🏫 <b>Класс/Группа:</b> {c} / {g}\n\n"
            f"📊 <b>Твоя статистика:</b>\n"
            f"🔥 <b>Дней подряд:</b> {user.current_streak}\n"
            f"✅ <b>Всего заданий:</b> {user.total_completed}\n"
            f"🏆 <b>Максимум в день:</b> {user.max_tasks_per_day}\n"
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="✏️ Изменить имя", callback_data="s_edit_name")
        builder.button(text="◀️ Назад", callback_data="s_panel")
        builder.adjust(1)

        if is_callback:
            await original_callback.message.edit_text(
                text, parse_mode="HTML", reply_markup=builder.as_markup()
            )
        else:
            await message.answer(
                text, parse_mode="HTML", reply_markup=builder.as_markup()
            )


@student_router.callback_query(F.data == "s_edit_name")
async def edit_name_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Введите свое новое <b>Имя</b>:", parse_mode="HTML", reply_markup=get_cancel_s()
    )
    await state.set_state(ChangeProfile.first_name)


@student_router.message(ChangeProfile.first_name, F.text)
async def edit_first_name(message: types.Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer(
        "Теперь введите новую <b>Фамилию</b>:",
        parse_mode="HTML",
        reply_markup=get_cancel_s(),
    )
    await state.set_state(ChangeProfile.last_name)


@student_router.message(ChangeProfile.last_name, F.text)
async def edit_last_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        user.first_name = data["first_name"]
        user.last_name = message.text
        await session.commit()
    await state.clear()
    await message.answer("✅ Имя и фамилия успешно изменены!")
    await send_role_panel(message, user.role, is_edit=False)


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

        builder = InlineKeyboardBuilder()
        if not rows:
            builder.button(text="◀️ В меню", callback_data="s_panel")
            return await callback.message.edit_text(
                "У тебя пока нет выполненных заданий.", reply_markup=builder.as_markup()
            )

        for sub, task in rows:
            grade_str = f"Оценка: {sub.grade}" if sub.grade else "⏳ На проверке"
            builder.button(
                text=f"📝 {task.title} ({grade_str})", callback_data=f"s_sub_{sub.id}"
            )

        builder.button(text="◀️ В меню", callback_data="s_panel")
        builder.adjust(1)

        await callback.message.edit_text(
            "✅ <b>Выполненные задания:</b>",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
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

        grade_str = str(sub.grade) if sub.grade else "⏳ Ещё не проверено"
        comment_str = sub.teacher_comment if sub.teacher_comment else "Нет комментария"

        text = (
            f"📝 <b>Задание:</b> {task.title}\n"
            f"📖 <b>Описание:</b> {task.description}\n\n"
            f"⭐️ <b>Твоя оценка:</b> {grade_str}\n"
            f"👨‍🏫 <b>Комментарий учителя:</b> {comment_str}"
        )
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ К списку", callback_data="s_completed")
        builder.adjust(1)
        await callback.message.edit_text(
            text, parse_mode="HTML", reply_markup=builder.as_markup()
        )


# ================= ВЫПОЛНЕНИЕ НОВЫХ ЗАДАНИЙ =================
@student_router.callback_query(F.data == "s_tasks")
async def show_tasks(callback: types.CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ В меню", callback_data="s_panel")

        if not user.class_name:
            return await callback.message.edit_text(
                "Учитель еще не добавил тебя в группу!",
                reply_markup=builder.as_markup(),
            )

        subq = select(Submission.task_id).where(Submission.student_id == user.id)
        result = await session.execute(
            select(Task).where(
                Task.class_name == user.class_name,
                Task.group_name == user.group_name,
                Task.id.not_in(subq),
            )
        )
        tasks = result.scalars().all()

        if not tasks:
            return await callback.message.edit_text(
                "🎉 Ура! У тебя нет невыполненных заданий на сегодня.",
                reply_markup=builder.as_markup(),
            )

        task = tasks[0]
        await callback.message.delete()

        await callback.message.answer(
            f"📝 <b>Задание:</b> {task.title}\n\n{task.description}", parse_mode="HTML"
        )

        if task.media_id:
            await callback.message.answer("👇 Вложение от учителя:")
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

        cancel_builder = InlineKeyboardBuilder()
        cancel_builder.button(text="❌ Отмена", callback_data="s_panel")
        await callback.message.answer(
            "Запиши и отправь свой ответ (Голосовое сообщение или Видео-кружок) 🎤",
            reply_markup=cancel_builder.as_markup(),
        )
        await state.update_data(task_id=task.id)
        await state.set_state(StudentTask.waiting_for_answer)


@student_router.message(
    StudentTask.waiting_for_answer, F.voice | F.video_note | F.video
)
async def receive_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_id = (
        message.voice.file_id
        if message.voice
        else (
            message.video_note.file_id if message.video_note else message.video.file_id
        )
    )
    media_type = (
        "voice" if message.voice else ("video_note" if message.video_note else "video")
    )

    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
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
            task_id=data["task_id"],
            student_id=message.from_user.id,
            media_id=media_id,
            media_type=media_type,
        )
        session.add(new_sub)
        await session.commit()

    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="Продолжить решать ➡️", callback_data="s_tasks")
    builder.button(text="◀️ В меню", callback_data="s_panel")
    builder.adjust(1)
    await message.answer(
        "✅ Отличная работа! Твой ответ отправлен учителю.",
        reply_markup=builder.as_markup(),
    )
