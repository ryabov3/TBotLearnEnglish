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
from states.states import StudentTask

student_router = Router()

# ================= УМНЫЙ РАСПРЕДЕЛИТЕЛЬ ПАНЕЛЕЙ =================
async def send_role_panel(message: types.Message, role: str, is_edit: bool = False):
    """Эта функция сама решает, какую клавиатуру показать пользователю"""
    builder = InlineKeyboardBuilder()
    
    if role in ["teacher", "admin"]:
        builder.button(text="📝 Создать задание", callback_data="t_new_task")
        builder.button(text="✅ Проверить ответы", callback_data="t_check_tasks")
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
        await message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

# ================= СТАРТ И МЕНЮ =================
@student_router.message(CommandStart())
async def cmd_start(message: types.Message):
    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        username = message.from_user.username or "Без_юзернейма"
        
        if not user:
            role = "admin" if message.from_user.id == ADMIN_ID else "student"
            user = User(id=message.from_user.id, username=username, role=role)
            session.add(user)
            await session.commit()
            await message.answer(f"Привет! 🇬🇧 Ты зарегистрирован как <b>{role}</b>.", parse_mode="HTML")
        else:
            if user.is_banned:
                return await message.answer("❌ Вы заблокированы администратором.")
            user.username = username
            await session.commit()
            
        await send_role_panel(message, user.role, is_edit=False)

@student_router.message(Command("menu"))
async def cmd_menu(message: types.Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        user = await session.get(User, message.from_user.id)
        if user and not user.is_banned:
            await send_role_panel(message, user.role, is_edit=False)

@student_router.callback_query(F.data == "s_panel")
async def back_to_student_panel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        if user and not user.is_banned:
            await send_role_panel(callback.message, user.role, is_edit=True)

# ================= ПРОФИЛЬ УЧЕНИКА =================
@student_router.message(Command("profile"))
async def cmd_profile(message: types.Message):
    await show_profile(message)

@student_router.callback_query(F.data == "s_profile")
async def inline_profile(callback: types.CallbackQuery):
    await show_profile(callback.message, is_callback=True, original_callback=callback)

async def show_profile(message: types.Message, is_callback=False, original_callback=None):
    async with SessionLocal() as session:
        user = await session.get(User, message.chat.id if is_callback else message.from_user.id)
        if not user or user.is_banned: return
        
        g = user.group_name if user.group_name else "Нет группы"
        c = user.class_name if user.class_name else "Нет класса"
        
        text = (
            f"👤 <b>Твой профиль:</b> @{user.username}\n"
            f"🎓 <b>Роль:</b> {user.role}\n"
            f"🏫 <b>Класс/Группа:</b> {c} / {g}\n\n"
            f"📊 <b>Твоя статистика:</b>\n"
            f"🔥 <b>Дней подряд:</b> {user.current_streak}\n"
            f"✅ <b>Всего заданий:</b> {user.total_completed}\n"
            f"🏆 <b>Максимум в день:</b> {user.max_tasks_per_day}\n"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="s_panel")
        
        if is_callback:
            await original_callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
        else:
            await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

# ================= ВЫПОЛНЕННЫЕ ЗАДАНИЯ (ИСТОРИЯ) =================
@student_router.callback_query(F.data == "s_completed")
async def show_completed_tasks(callback: types.CallbackQuery):
    async with SessionLocal() as session:
        # Получаем последние 10 выполненных заданий ученика
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
            return await callback.message.edit_text("У тебя пока нет выполненных заданий.", reply_markup=builder.as_markup())
        
        for sub, task in rows:
            # Формируем текст кнопки (название + статус)
            grade_str = f"Оценка: {sub.grade}" if sub.grade else "⏳ На проверке"
            btn_text = f"📝 {task.title} ({grade_str})"
            builder.button(text=btn_text, callback_data=f"s_sub_{sub.id}")
            
        builder.button(text="◀️ В меню", callback_data="s_panel")
        builder.adjust(1)
        
        await callback.message.edit_text(
            "✅ <b>Твои последние выполненные задания:</b>\nНажми на задание, чтобы посмотреть детали и комментарий учителя.", 
            parse_mode="HTML", 
            reply_markup=builder.as_markup()
        )

# Показ конкретного выполненного задания
@student_router.callback_query(F.data.startswith("s_sub_"))
async def show_submission_details(callback: types.CallbackQuery):
    sub_id = int(callback.data.split("_")[2])
    
    async with SessionLocal() as session:
        result = await session.execute(
            select(Submission, Task)
            .join(Task, Submission.task_id == Task.id)
            .where(Submission.id == sub_id)
        )
        row = result.first()
        if not row:
            return await callback.answer("Задание не найдено!")
        
        sub, task = row
        
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
        builder.button(text="🏠 В меню", callback_data="s_panel")
        builder.adjust(1)
        
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

# ================= ВЫПОЛНЕНИЕ НОВЫХ ЗАДАНИЙ =================
@student_router.callback_query(F.data == "s_tasks")
async def show_tasks(callback: types.CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        user = await session.get(User, callback.from_user.id)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ В меню", callback_data="s_panel")
        
        if not user.class_name:
            return await callback.message.edit_text("Учитель еще не добавил тебя в группу!", reply_markup=builder.as_markup())

        subq = select(Submission.task_id).where(Submission.student_id == user.id)
        result = await session.execute(
            select(Task).where(
                Task.class_name == user.class_name,
                Task.group_name == user.group_name,
                Task.id.not_in(subq)
            )
        )
        tasks = result.scalars().all()

        if not tasks:
            return await callback.message.edit_text("🎉 Ура! У тебя нет невыполненных заданий на сегодня.", reply_markup=builder.as_markup())

        task = tasks[0] 
        await callback.message.delete()
        
        await callback.message.answer(f"📝 <b>Задание:</b> {task.title}\n\n{task.description}", parse_mode="HTML")
        
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
        await callback.message.answer("Запиши и отправь свой ответ (Голосовое сообщение или Видео-кружок) 🎤", reply_markup=cancel_builder.as_markup())
        await state.update_data(task_id=task.id)
        await state.set_state(StudentTask.waiting_for_answer)

@student_router.message(StudentTask.waiting_for_answer, F.voice | F.video_note | F.video)
async def receive_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_id = message.voice.file_id if message.voice else (message.video_note.file_id if message.video_note else message.video.file_id)
    media_type = "voice" if message.voice else ("video_note" if message.video_note else "video")
    
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
            task_id=data['task_id'],
            student_id=message.from_user.id,
            media_id=media_id,
            media_type=media_type
        )
        session.add(new_sub)
        await session.commit()
        
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="Продолжить решать ➡️", callback_data="s_tasks")
    builder.button(text="◀️ В меню", callback_data="s_panel")
    builder.adjust(1)
    await message.answer("✅ Отличная работа! Твой ответ отправлен учителю.", reply_markup=builder.as_markup())