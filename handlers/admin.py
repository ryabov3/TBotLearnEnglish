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
    builder.button(text="👨‍🏫 Список учителей", callback_data="admtl_0") 
    builder.button(text="📢 Сообщение ученикам", callback_data="admin_broad_student")
    builder.button(text="📢 Сообщение учителям", callback_data="admin_broad_teacher")
    builder.button(text="✉️ Личное сообщение", callback_data="admin_pml_0") # Новая кнопка
    builder.button(text="🔍 Действия пользователя", callback_data="admin_actions")
    builder.button(text="🔨 Забанить", callback_data="admin_ban")
    builder.button(text="🕊 Разбанить", callback_data="admin_unban")
    builder.adjust(2, 1, 2, 1, 1, 2)

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

# ================= 👨‍🏫 ИЕРАРХИЯ: УЧИТЕЛЯ -> КЛАССЫ -> ГРУППЫ -> УЧЕНИКИ =================

# 1. Список учителей
@admin_router.callback_query(F.data.startswith("admtl_"))
async def admin_list_teachers_pg(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    per_page = 5
    
    async with SessionLocal() as session:
        # Берем и учителей и админов (так как админы тоже могут создавать группы)
        teachers = (await session.execute(select(User).where(User.role.in_(["teacher", "admin"])))).scalars().all()

    if not teachers:
        b = InlineKeyboardBuilder()
        b.button(text="◀️ Назад", callback_data="admin_back")
        return await callback.message.edit_text("В системе пока нет учителей.", reply_markup=b.as_markup())

    total_pages = max(1, (len(teachers) + per_page - 1) // per_page)
    current_teachers = teachers[page*per_page : (page+1)*per_page]

    b = InlineKeyboardBuilder()
    for t in current_teachers:
        name = f"{t.first_name or ''} {t.last_name or ''}".strip() or t.username or str(t.id)
        b.button(text=f"👨‍🏫 {name}", callback_data=f"admt_{t.id}_0")
    b.adjust(1)

    nav = InlineKeyboardBuilder()
    if page > 0: nav.button(text="⬅️ Пред.", callback_data=f"admtl_{page-1}")
    if page < total_pages - 1: nav.button(text="След. ➡️", callback_data=f"admtl_{page+1}")
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text="◀️ В панель", callback_data="admin_back")
    b.attach(back)

    await callback.message.edit_text(f"👨‍🏫 <b>Список учителей</b> (Стр. {page+1}/{total_pages}):\nВыберите учителя:", parse_mode="HTML", reply_markup=b.as_markup())

# 2. Список классов конкретного учителя
@admin_router.callback_query(F.data.startswith("admt_"))
async def admin_list_classes_pg(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    teacher_id = int(parts[1])
    page = int(parts[2])
    per_page = 5

    async with SessionLocal() as session:
        teacher = await session.get(User, teacher_id)
        groups = (await session.execute(select(StudyGroup).where(StudyGroup.teacher_id == teacher_id))).scalars().all()

    # Фильтруем только уникальные классы (убираем дубликаты групп)
    unique_classes = {}
    for g in groups:
        if g.class_name not in unique_classes:
            unique_classes[g.class_name] = g

    distinct_groups = list(unique_classes.values())

    if not distinct_groups:
        b = InlineKeyboardBuilder()
        b.button(text="◀️ К учителям", callback_data="admtl_0")
        return await callback.message.edit_text("У этого учителя пока нет классов.", reply_markup=b.as_markup())

    total_pages = max(1, (len(distinct_groups) + per_page - 1) // per_page)
    current_groups = distinct_groups[page*per_page : (page+1)*per_page]

    b = InlineKeyboardBuilder()
    for g in current_groups:
        b.button(text=f"🏫 Класс: {g.class_name}", callback_data=f"admc_{g.id}_0")
    b.adjust(1)

    nav = InlineKeyboardBuilder()
    if page > 0: nav.button(text="⬅️ Пред.", callback_data=f"admt_{teacher_id}_{page-1}")
    if page < total_pages - 1: nav.button(text="След. ➡️", callback_data=f"admt_{teacher_id}_{page+1}")
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text="◀️ К учителям", callback_data="admtl_0")
    b.attach(back)

    t_name = f"{teacher.first_name or ''} {teacher.last_name or ''}".strip() or teacher.username or "Учитель"
    await callback.message.edit_text(f"👨‍🏫 Учитель: <b>{t_name}</b>\n🏫 Выберите класс (Стр. {page+1}/{total_pages}):", parse_mode="HTML", reply_markup=b.as_markup())

# 3. Список групп в классе
@admin_router.callback_query(F.data.startswith("admc_"))
async def admin_list_groups_pg(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    base_group_id = int(parts[1])
    page = int(parts[2])
    per_page = 5

    async with SessionLocal() as session:
        base_group = await session.get(StudyGroup, base_group_id)
        if not base_group:
            return await callback.answer("Ошибка: Класс не найден", show_alert=True)
        
        # Ищем все группы для этого учителя и этого названия класса
        groups = (await session.execute(
            select(StudyGroup).where(
                StudyGroup.teacher_id == base_group.teacher_id, 
                StudyGroup.class_name == base_group.class_name
            )
        )).scalars().all()

    if not groups:
        b = InlineKeyboardBuilder()
        b.button(text="◀️ Назад", callback_data=f"admt_{base_group.teacher_id}_0")
        return await callback.message.edit_text("В этом классе нет групп.", reply_markup=b.as_markup())

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page*per_page : (page+1)*per_page]

    b = InlineKeyboardBuilder()
    for g in current_groups:
        b.button(text=f"👥 Группа: {g.group_name}", callback_data=f"admg_{g.id}_0")
    b.adjust(1)

    nav = InlineKeyboardBuilder()
    if page > 0: nav.button(text="⬅️ Пред.", callback_data=f"admc_{base_group_id}_{page-1}")
    if page < total_pages - 1: nav.button(text="След. ➡️", callback_data=f"admc_{base_group_id}_{page+1}")
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text="◀️ К классам", callback_data=f"admt_{base_group.teacher_id}_0")
    b.attach(back)

    await callback.message.edit_text(f"🏫 Класс: <b>{base_group.class_name}</b>\n👥 Выберите группу (Стр. {page+1}/{total_pages}):", parse_mode="HTML", reply_markup=b.as_markup())

# 4. Список учеников в группе
@admin_router.callback_query(F.data.startswith("admg_"))
async def admin_list_students_pg(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    group_id = int(parts[1])
    page = int(parts[2])
    per_page = 5

    async with SessionLocal() as session:
        group = await session.get(StudyGroup, group_id)
        if not group:
            return await callback.answer("Ошибка: Группа не найдена", show_alert=True)
        
        students = (await session.execute(
            select(User).where(
                User.class_name == group.class_name,
                User.group_name == group.group_name,
                User.role == "student"
            )
        )).scalars().all()

    if not students:
        b = InlineKeyboardBuilder()
        b.button(text="◀️ Назад", callback_data=f"admc_{group_id}_0")
        return await callback.message.edit_text(f"В группе <b>{group.group_name}</b> пока нет учеников.", parse_mode="HTML", reply_markup=b.as_markup())

    total_pages = max(1, (len(students) + per_page - 1) // per_page)
    current_students = students[page*per_page : (page+1)*per_page]

    b = InlineKeyboardBuilder()
    for s in current_students:
        name = f"{s.first_name or ''} {s.last_name or ''}".strip() or s.username or str(s.id)
        b.button(text=f"👤 {name}", callback_data=f"adms_{s.id}_{group_id}")
    b.adjust(1)

    nav = InlineKeyboardBuilder()
    if page > 0: nav.button(text="⬅️ Пред.", callback_data=f"admg_{group_id}_{page-1}")
    if page < total_pages - 1: nav.button(text="След. ➡️", callback_data=f"admg_{group_id}_{page+1}")
    nav.adjust(2)
    b.attach(nav)

    back = InlineKeyboardBuilder()
    back.button(text="◀️ К группам", callback_data=f"admc_{group_id}_0")
    b.attach(back)

    await callback.message.edit_text(
        f"🏫 Класс: <b>{group.class_name}</b> | 👥 Группа: <b>{group.group_name}</b>\n"
        f"Выберите ученика (Стр. {page+1}/{total_pages}):", 
        parse_mode="HTML", reply_markup=b.as_markup()
    )

# 5. Профиль ученика
@admin_router.callback_query(F.data.startswith("adms_"))
async def admin_student_profile(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    student_id = int(parts[1])
    group_id = int(parts[2])

    async with SessionLocal() as session:
        user = await session.get(User, student_id)
        if not user:
            return await callback.answer("Ученик не найден", show_alert=True)
        
        text = f"🔍 <b>Досье ученика:</b>\n"
        text += f"Имя: {user.first_name or 'Нет'} {user.last_name or 'Нет'} (@{user.username or 'Нет'})\n"
        text += f"Статус: {'🚫 Забанен' if user.is_banned else '✅ Активен'}\n"
        text += f"🏫 Группа: {user.class_name or 'Нет'} - {user.group_name or 'Нет'}\n\n"
        text += f"🔥 Дней подряд: {user.current_streak}\n"
        text += f"✅ Всего решено заданий: {user.total_completed}\n"
        text += f"🏆 Максимум заданий в день: {user.max_tasks_per_day}\n\n"
        
        subs = (await session.execute(
            select(Submission, Task).join(Task, Submission.task_id == Task.id)
            .where(Submission.student_id == user.id).order_by(Submission.id.desc()).limit(3)
        )).all()
        
        text += "<b>Последние 3 выполненные задания:</b>\n"
        if not subs: text += "<i>Пока нет ответов.</i>"
        for sub, task in subs:
            grade = f"Оценка: {sub.grade}" if sub.grade else "⏳ Не проверено"
            text += f"• {task.topic} | {task.title} ({grade})\n"

    b = InlineKeyboardBuilder()
    b.button(text="◀️ К списку учеников", callback_data=f"admg_{group_id}_0")
    b.adjust(1)

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=b.as_markup())

# ================= КОНЕЦ ИЕРАРХИИ =================

# ================= ЛИЧНЫЕ СООБЩЕНИЯ =================
@admin_router.callback_query(F.data.startswith("admin_pml_"))
async def admin_pm_list(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    per_page = 5
    
    async with SessionLocal() as session:
        # Берем всех пользователей кроме самого админа
        users = (await session.execute(
            select(User).where(User.id != callback.from_user.id).order_by(User.role, User.id)
        )).scalars().all()
        
    if not users:
        b = InlineKeyboardBuilder()
        b.button(text="◀️ В панель", callback_data="admin_back")
        return await callback.message.edit_text("В базе данных пока нет других пользователей.", reply_markup=b.as_markup())

    total_pages = max(1, (len(users) + per_page - 1) // per_page)
    current_users = users[page*per_page : (page+1)*per_page]
    
    b = InlineKeyboardBuilder()
    for u in current_users:
        emoji = "👨‍🏫" if u.role in ["teacher", "admin"] else "👨‍🎓"
        uname = f"(@{u.username})" if u.username else ""
        name = f"{u.first_name or ''} {u.last_name or ''}".strip() or str(u.id)
        btn_text = f"{emoji} {uname} {name}".strip()
        b.button(text=btn_text, callback_data=f"admin_pmu_{u.id}")
    b.adjust(1)
    
    nav = InlineKeyboardBuilder()
    if page > 0: nav.button(text="⬅️ Пред.", callback_data=f"admin_pml_{page-1}")
    if page < total_pages - 1: nav.button(text="След. ➡️", callback_data=f"admin_pml_{page+1}")
    nav.adjust(2)
    b.attach(nav)
    
    back = InlineKeyboardBuilder()
    back.button(text="◀️ В панель", callback_data="admin_back")
    b.attach(back)
    
    await callback.message.edit_text(
        f"✉️ <b>Личные сообщения</b>\nВыберите пользователя для отправки сообщения (Стр. {page+1}/{total_pages}):", 
        parse_mode="HTML", 
        reply_markup=b.as_markup()
    )

@admin_router.callback_query(F.data.startswith("admin_pmu_"))
async def admin_pm_user(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[2])
    
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        
    if not user:
        return await callback.answer("Ошибка: Пользователь не найден.", show_alert=True)
        
    await state.update_data(pm_target_id=user_id)
    await state.set_state(AdminPanel.waiting_for_personal_message)
    
    b = InlineKeyboardBuilder()
    b.button(text="❌ Отмена", callback_data="admin_pml_0")
    
    emoji = "👨‍🏫" if user.role in ["teacher", "admin"] else "👨‍🎓"
    uname = f"(@{user.username})" if user.username else ""
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user.id)
    
    await callback.message.edit_text(
        f"Напишите текст сообщения, которое будет отправлено пользователю:\n<b>{emoji} {uname} {name}</b>", 
        parse_mode="HTML",
        reply_markup=b.as_markup()
    )

@admin_router.message(AdminPanel.waiting_for_personal_message)
async def process_personal_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("pm_target_id")
    
    full_message = f"🔔 <b>Администратор отправил Вам личное сообщение:</b>\n\n{message.text}"
    
    try:
        await message.bot.send_message(target_id, full_message, parse_mode="HTML")
        await message.answer("✅ Личное сообщение успешно доставлено!")
    except Exception:
        await message.answer("❌ Ошибка при отправке. Возможно, пользователь заблокировал бота или удалил аккаунт.")
        
    await state.clear()
    await show_admin_panel(message, is_edit=False)
# ================= КОНЕЦ ЛИЧНЫХ СООБЩЕНИЙ =================


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

# ================= ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ (РУЧНОЙ ПОИСК) =================
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