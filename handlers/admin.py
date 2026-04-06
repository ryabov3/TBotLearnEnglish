# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from config import ADMINS_ID
from database.engine import SessionLocal
from database.models import User, StudyGroup, Task, Submission
from states.states import AdminPanel

admin_router = Router()

def get_cancel_admin():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin_back")
    return builder.as_markup()

async def show_admin_panel(message: types.Message, is_edit: bool = False):
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Назначить учителя", callback_data="admin_add_teacher")
    builder.button(text="➖ Убрать учителя", callback_data="admin_rem_teacher")
    builder.button(text="👨‍🏫 Список учителей", callback_data="admin_list_teachers")
    builder.button(text="📢 Сообщение ученикам", callback_data="admin_broad_student")
    builder.button(text="📢 Сообщение учителям", callback_data="admin_broad_teacher")
    builder.button(text="🔍 Действия пользователя", callback_data="admin_actions")
    builder.button(text="🔨 Забанить", callback_data="admin_ban")
    builder.button(text="🕊 Разбанить", callback_data="admin_unban")
    builder.adjust(2, 1, 2, 1, 2)

    text = "<b>🛠 Панель администратора</b>\nВыберите действие:"
    if is_edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMINS_ID:
        return await message.answer("❌ У вас нет прав администратора.")
    await show_admin_panel(message, is_edit=False)

@admin_router.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_admin_panel(callback.message, is_edit=True)

@admin_router.callback_query(F.data == "admin_list_teachers")
async def list_teachers(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.role == "teacher"))
        teachers = result.scalars().all()

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="admin_back")

    if not teachers:
        return await callback.message.edit_text(
            "В системе пока нет учителей.", reply_markup=builder.as_markup()
        )

    text = "👨‍🏫 <b>Список учителей:</b>\n\n"
    for t in teachers:
        fname = t.first_name or "Без_имени"
        lname = t.last_name or "Без_фамилии"
        uname = f"@{t.username}" if t.username else "нет_юзернейма"
        text += f"• {fname} {lname} ({uname})\n"

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@admin_router.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    if action == "admin_add_teacher":
        await callback.message.edit_text("Введите @юзернейм пользователя для назначения учителем:", reply_markup=get_cancel_admin())
        await state.set_state(AdminPanel.waiting_for_username_teacher)
    elif action == "admin_rem_teacher":
        await callback.message.edit_text("Введите @юзернейм для снятия роли учителя:", reply_markup=get_cancel_admin())
        await state.set_state(AdminPanel.waiting_for_username_remove)
    elif action == "admin_ban":
        await callback.message.edit_text("Введите @юзернейм для бана:", reply_markup=get_cancel_admin())
        await state.set_state(AdminPanel.waiting_for_username_ban)
    elif action == "admin_unban":
        await callback.message.edit_text("Введите @юзернейм для разбана:", reply_markup=get_cancel_admin())
        await state.set_state(AdminPanel.waiting_for_username_unban)
    elif action == "admin_broad_student":
        await state.update_data(broadcast_target="student")
        await callback.message.edit_text("Напишите сообщение, которое будет отправлено <b>всем ученикам</b>:", parse_mode="HTML", reply_markup=get_cancel_admin())
        await state.set_state(AdminPanel.waiting_for_broadcast_text)
    elif action == "admin_broad_teacher":
        await state.update_data(broadcast_target="teacher")
        await callback.message.edit_text("Напишите сообщение, которое будет отправлено <b>всем учителям</b>:", parse_mode="HTML", reply_markup=get_cancel_admin())
        await state.set_state(AdminPanel.waiting_for_broadcast_text)
    elif action == "admin_actions":
        await callback.message.edit_text("Введите @юзернейм пользователя (учителя или ученика), чтобы просмотреть его профиль и действия:", reply_markup=get_cancel_admin())
        await state.set_state(AdminPanel.waiting_for_username_actions)
    await callback.answer()

# ================= ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ =================
@admin_router.message(AdminPanel.waiting_for_username_actions)
async def check_user_actions(message: types.Message, state: FSMContext):
    username = message.text.replace("@", "")
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В панель", callback_data="admin_back")
    
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        
        if not user:
            return await message.answer(f"❌ Пользователь @{username} не найден в базе данных.", reply_markup=builder.as_markup())
            
        text = f"🔍 <b>Досье на пользователя:</b>\n"
        text += f"Имя: {user.first_name} {user.last_name} (@{username})\n"
        text += f"Роль: <b>{user.role.upper()}</b>\n"
        text += f"Статус: {'🚫 Забанен' if user.is_banned else '✅ Активен'}\n\n"
        
        if user.role == "student":
            text += f"🏫 Группа: {user.class_name or 'Нет'} - {user.group_name or 'Нет'}\n"
            text += f"🔥 Дней подряд: {user.current_streak}\n"
            text += f"✅ Всего решено заданий: {user.total_completed}\n"
            text += f"🏆 Максимум заданий в день: {user.max_tasks_per_day}\n\n"
            
            subs = (await session.execute(
                select(Submission, Task).join(Task, Submission.task_id == Task.id)
                .where(Submission.student_id == user.id).order_by(Submission.id.desc()).limit(3)
            )).all()
            
            text += "<b>Последние выполненные задания:</b>\n"
            if not subs: text += "<i>Пока нет ответов.</i>"
            for sub, task in subs:
                grade = f"Оценка: {sub.grade}" if sub.grade else "⏳ Не проверено"
                text += f"• {task.topic} | {task.title} ({grade})\n"
                
        elif user.role in ["teacher", "admin"]:
            groups = (await session.execute(select(StudyGroup).where(StudyGroup.teacher_id == user.id))).scalars().all()
            tasks = (await session.execute(select(Task).where(Task.teacher_id == user.id))).scalars().all()
            
            text += f"👥 Создано групп: <b>{len(groups)}</b>\n"
            text += f"📝 Создано заданий (всего шагов): <b>{len(tasks)}</b>\n\n"
            text += "<b>Список групп:</b>\n"
            if not groups: text += "<i>Нет созданных групп.</i>"
            for g in groups:
                text += f"• {g.class_name} - {g.group_name}\n"

    await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())
    await state.clear()

# ================= РАССЫЛКА =================
@admin_router.message(AdminPanel.waiting_for_broadcast_text)
async def process_broadcast(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("broadcast_target")
    
    async with SessionLocal() as session:
        users = (await session.execute(select(User).where(User.role == target, User.is_banned == False))).scalars().all()
        
    count = 0
    prefix = "👨‍🎓" if target == "student" else "👨‍🏫"
    full_message = f"🔔 <b>Уведомление от Администрации:</b>\n\n{message.text}"
    
    for u in users:
        try:
            await message.bot.send_message(u.id, full_message, parse_mode="HTML")
            count += 1
        except Exception:
            pass # Пользователь мог заблокировать бота
            
    await message.answer(f"✅ Успешно!\nСообщение доставлено {count} пользователям с ролью '{target}'.")
    await state.clear()
    await show_admin_panel(message, is_edit=False)


# ================= ИЗМЕНЕНИЕ ДАННЫХ =================
async def update_user_by_username(
    message: types.Message, state: FSMContext, field: str, value
):
    username = message.text.replace("@", "")
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден. Он должен нажать /start.")
        else:
            setattr(user, field, value)
            await session.commit()
            await message.answer(f"✅ Данные пользователя @{username} обновлены!")

    await state.clear()
    await show_admin_panel(message, is_edit=False)

@admin_router.message(AdminPanel.waiting_for_username_teacher)
async def set_teacher(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "role", "teacher")

@admin_router.message(AdminPanel.waiting_for_username_remove)
async def rem_teacher(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "role", "student")

@admin_router.message(AdminPanel.waiting_for_username_ban)
async def ban_user(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "is_banned", True)

@admin_router.message(AdminPanel.waiting_for_username_unban)
async def unban_user(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "is_banned", False)