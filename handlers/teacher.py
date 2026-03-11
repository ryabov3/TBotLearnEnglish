# handlers/teacher.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from database.engine import SessionLocal
from database.models import User, StudyGroup, Task, Submission
from states.states import TeacherGroup, TeacherTask, TeacherCheck, TeacherAddStudent

teacher_router = Router()

def get_cancel_t():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="t_menu")
    return builder.as_markup()

async def is_teacher(user_id: int) -> bool:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        return user and user.role in ["teacher", "admin"]

@teacher_router.callback_query(F.data == "t_menu")
async def teacher_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать задание", callback_data="t_new_task")
    builder.button(text="✅ Проверить ответы", callback_data="t_check_tasks_0")
    builder.button(text="📊 Статистика", callback_data="t_st_pg_0")
    builder.button(text="➕ Создать группу", callback_data="t_add_group")
    builder.button(text="👤 Добавить ученика", callback_data="t_add_student")
    builder.adjust(1)
    await callback.message.edit_text("👨‍🏫 <b>Панель Учителя</b>\nВыберите действие:", parse_mode="HTML", reply_markup=builder.as_markup())

# ================= 1. СОЗДАНИЕ ГРУППЫ =================
@teacher_router.callback_query(F.data == "t_add_group")
async def start_add_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи название класса (например, 5А):", reply_markup=get_cancel_t())
    await state.set_state(TeacherGroup.class_name)

@teacher_router.message(TeacherGroup.class_name, F.text)
async def process_class_name(message: types.Message, state: FSMContext):
    await state.update_data(class_name=message.text)
    await message.answer("Введи название группы (например, Группа 1):", reply_markup=get_cancel_t())
    await state.set_state(TeacherGroup.group_name)

@teacher_router.message(TeacherGroup.group_name, F.text)
async def process_group_name(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        new_group = StudyGroup(
            teacher_id=message.from_user.id,
            class_name=data['class_name'],
            group_name=message.text
        )
        session.add(new_group)
        await session.commit()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В меню", callback_data="t_menu")
    await message.answer("✅ Класс и группа успешно сохранены!", reply_markup=builder.as_markup())
    await state.clear()

# ================= 2. ДОБАВЛЕНИЕ УЧЕНИКА В ГРУППУ =================
@teacher_router.callback_query(F.data == "t_add_student")
async def start_add_student(callback: types.CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        result = await session.execute(select(StudyGroup).where(StudyGroup.teacher_id == callback.from_user.id))
        groups = result.scalars().all()
        
    if not groups:
        return await callback.message.edit_text("❌ У вас еще нет групп. Сначала создайте группу.")

    builder = InlineKeyboardBuilder()
    for g in groups:
        builder.button(text=f"{g.class_name} - {g.group_name}", callback_data=f"sel_group_{g.id}")
    builder.button(text="◀️ Назад", callback_data="t_menu")
    builder.adjust(1)
    await callback.message.edit_text("Выберите класс и группу, куда добавить ученика:", reply_markup=builder.as_markup())
    await state.set_state(TeacherAddStudent.select_group)

@teacher_router.callback_query(TeacherAddStudent.select_group, F.data.startswith("sel_group_"))
async def add_student_group_selected(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[2])
    async with SessionLocal() as session:
        group = await session.get(StudyGroup, group_id)
        await state.update_data(class_name=group.class_name, group_name=group.group_name)
    await callback.message.edit_text(f"Группа выбрана ({group.class_name} - {group.group_name}).\nТеперь отправьте @юзернейм ученика:", reply_markup=get_cancel_t())
    await state.set_state(TeacherAddStudent.waiting_for_username)

@teacher_router.message(TeacherAddStudent.waiting_for_username, F.text)
async def add_student_username(message: types.Message, state: FSMContext):
    username = message.text.replace("@", "")
    data = await state.get_data()
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        student = result.scalar_one_or_none()
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ В меню", callback_data="t_menu")
        
        if not student:
            await message.answer(f"❌ Ученик @{username} не найден. Он должен запустить бота.", reply_markup=builder.as_markup())
        else:
            student.class_name = data['class_name']
            student.group_name = data['group_name']
            await session.commit()
            await message.answer(f"✅ Ученик @{username} успешно добавлен в {data['class_name']} - {data['group_name']}!", reply_markup=builder.as_markup())
    await state.clear()

# ================= 3. СОЗДАНИЕ ЗАДАНИЯ =================
@teacher_router.callback_query(F.data == "t_new_task")
async def start_new_task(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи название темы (например, 'Хобби - Спорт'):", reply_markup=get_cancel_t())
    await state.set_state(TeacherTask.title)

@teacher_router.message(TeacherTask.title, F.text)
async def task_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Напиши текстовое описание задания:", reply_markup=get_cancel_t())
    await state.set_state(TeacherTask.description)

@teacher_router.message(TeacherTask.description, F.text)
async def task_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить медиа", callback_data="skip_media")
    builder.button(text="❌ Отмена", callback_data="t_menu")
    builder.adjust(1)
    await message.answer("Отправь файл с примером (Фото, Видео, Аудио, Голосовое или Кружок).\nЕсли медиа не нужно, нажми «Пропустить».", reply_markup=builder.as_markup())
    await state.set_state(TeacherTask.media)

@teacher_router.callback_query(TeacherTask.media, F.data == "skip_media")
async def skip_media(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(media_id=None, media_type=None)
    await ask_for_groups(callback.message, state, callback.from_user.id)
    await callback.answer()

@teacher_router.message(TeacherTask.media, F.photo | F.video | F.audio | F.voice | F.video_note | F.document)
async def task_media(message: types.Message, state: FSMContext):
    media_id = None
    media_type = None

    if message.photo: media_id, media_type = message.photo[-1].file_id, "photo"
    elif message.video: media_id, media_type = message.video.file_id, "video"
    elif message.audio: media_id, media_type = message.audio.file_id, "audio"
    elif message.voice: media_id, media_type = message.voice.file_id, "voice"
    elif message.video_note: media_id, media_type = message.video_note.file_id, "video_note"
    elif message.document: media_id, media_type = message.document.file_id, "document"

    await state.update_data(media_id=media_id, media_type=media_type)
    await ask_for_groups(message, state, message.from_user.id)

async def ask_for_groups(message_or_callback: types.Message, state: FSMContext, teacher_id: int):
    data = await state.get_data()
    selected = data.get('selected_group_ids', [])

    async with SessionLocal() as session:
        result = await session.execute(select(StudyGroup).where(StudyGroup.teacher_id == teacher_id))
        groups = result.scalars().all()

    if not groups:
        await state.clear()
        if isinstance(message_or_callback, types.Message):
            return await message_or_callback.answer("❌ Сначала создайте классы в панели управления.")
        else:
            return await message_or_callback.edit_text("❌ Сначала создайте классы в панели управления.")

    builder = InlineKeyboardBuilder()
    for g in groups:
        mark = "✅ " if g.id in selected else ""
        builder.button(text=f"{mark}{g.class_name} - {g.group_name}", callback_data=f"tg_group_{g.id}")
    builder.button(text="Отправить задание 🚀", callback_data="confirm_task")
    builder.button(text="❌ Отмена", callback_data="t_menu")
    builder.adjust(1)

    text = "Выбери классы и группы для этого задания и нажми 'Отправить':"
    if isinstance(message_or_callback, types.Message):
        await message_or_callback.answer(text, reply_markup=builder.as_markup())
    else:
        await message_or_callback.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(TeacherTask.select_groups)

@teacher_router.callback_query(TeacherTask.select_groups, F.data.startswith("tg_group_"))
async def toggle_group(callback: types.CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    selected = data.get('selected_group_ids', [])
    
    if group_id in selected: selected.remove(group_id)
    else: selected.append(group_id)
        
    await state.update_data(selected_group_ids=selected)
    await ask_for_groups(callback.message, state, callback.from_user.id)
    await callback.answer()

@teacher_router.callback_query(TeacherTask.select_groups, F.data == "confirm_task")
async def confirm_task(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = data.get('selected_group_ids', [])
    if not selected_ids: return await callback.answer("❗ Выберите хотя бы одну группу!", show_alert=True)
        
    async with SessionLocal() as session:
        for gid in selected_ids:
            group = await session.get(StudyGroup, gid)
            new_task = Task(
                teacher_id=callback.from_user.id,
                title=data['title'],
                description=data['description'],
                media_id=data.get('media_id'),
                media_type=data.get('media_type'),
                class_name=group.class_name,
                group_name=group.group_name
            )
            session.add(new_task)
        await session.commit()
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В меню", callback_data="t_menu")
    await callback.message.edit_text("✅ Задание успешно создано и разослано выбранным группам!", reply_markup=builder.as_markup())

# ================= 4. ПРОВЕРКА ЗАДАНИЙ =================
@teacher_router.callback_query(F.data.startswith("t_check_tasks_"))
async def check_tasks_groups(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    per_page = 5
    
    async with SessionLocal() as session:
        result = await session.execute(select(StudyGroup).where(StudyGroup.teacher_id == callback.from_user.id))
        groups = result.scalars().all()

    if not groups:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ В меню", callback_data="t_menu")
        return await callback.message.edit_text("У вас пока нет созданных групп.", reply_markup=builder.as_markup())

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page*per_page : (page+1)*per_page]

    builder = InlineKeyboardBuilder()
    for g in current_groups:
        builder.button(text=f"📂 {g.class_name} - {g.group_name}", callback_data=f"t_chk_g_{g.id}")
    builder.adjust(1)
    
    nav_builder = InlineKeyboardBuilder()
    if page > 0: nav_builder.button(text="⬅️ Пред.", callback_data=f"t_check_tasks_{page-1}")
    if page < total_pages - 1: nav_builder.button(text="След. ➡️", callback_data=f"t_check_tasks_{page+1}")
    nav_builder.adjust(2)
    builder.attach(nav_builder)
    
    back_builder = InlineKeyboardBuilder()
    back_builder.button(text="🏠 В меню", callback_data="t_menu")
    builder.attach(back_builder)

    await callback.message.edit_text(f"Выберите группу для проверки (Страница {page+1} из {total_pages}):", reply_markup=builder.as_markup())

@teacher_router.callback_query(F.data.startswith("t_chk_g_"))
async def check_tasks_in_group(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    async with SessionLocal() as session:
        group = await session.get(StudyGroup, group_id)
        result = await session.execute(
            select(Task).where(
                Task.class_name == group.class_name,
                Task.group_name == group.group_name,
                Task.teacher_id == callback.from_user.id
            )
        )
        tasks = result.scalars().all()

    builder = InlineKeyboardBuilder()
    if not tasks:
        builder.button(text="◀️ Назад к группам", callback_data="t_check_tasks_0")
        return await callback.message.edit_text(f"В группе <b>{group.class_name} - {group.group_name}</b> нет заданий.", parse_mode="HTML", reply_markup=builder.as_markup())

    for t in tasks:
        builder.button(text=f"📝 {t.title}", callback_data=f"t_chk_t_{t.id}")
    builder.adjust(1)

    back_builder = InlineKeyboardBuilder()
    back_builder.button(text="◀️ Назад", callback_data="t_check_tasks_0")
    builder.attach(back_builder)

    await callback.message.edit_text(f"Группа: <b>{group.class_name} - {group.group_name}</b>\nВыберите задание:", parse_mode="HTML", reply_markup=builder.as_markup())

@teacher_router.callback_query(F.data.startswith("t_chk_t_"))
async def check_tasks_students(callback: types.CallbackQuery):
    task_id = int(callback.data.split("_")[-1])
    async with SessionLocal() as session:
        task = await session.get(Task, task_id)
        result = await session.execute(
            select(Submission, User)
            .join(User, Submission.student_id == User.id)
            .where(Submission.task_id == task_id, Submission.grade == None)
        )
        rows = result.all()

    builder = InlineKeyboardBuilder()
    if not rows:
        builder.button(text="◀️ Назад к группам", callback_data="t_check_tasks_0")
        return await callback.message.edit_text("🎉 Все ответы к этому заданию уже проверены!", reply_markup=builder.as_markup())

    for sub, student in rows:
        name = f"{student.first_name} {student.last_name} (@{student.username or 'без_юзернейма'})"
        builder.button(text=name, callback_data=f"t_chk_s_{sub.id}")
    builder.adjust(1)

    back_builder = InlineKeyboardBuilder()
    back_builder.button(text="🏠 В меню", callback_data="t_menu")
    builder.attach(back_builder)

    caption = (
        f"📝 <b>Задание:</b> {task.title}\n"
        f"📖 <b>Описание:</b> {task.description}\n\n"
        f"👇 <b>Выберите ученика для проверки:</b>"
    )

    await callback.message.delete() 

    if task.media_id:
        if task.media_type == "photo":
            await callback.message.answer_photo(task.media_id, caption=caption, parse_mode="HTML", reply_markup=builder.as_markup())
        elif task.media_type == "video":
            await callback.message.answer_video(task.media_id, caption=caption, parse_mode="HTML", reply_markup=builder.as_markup())
        elif task.media_type == "voice":
            await callback.message.answer_voice(task.media_id, caption=caption, parse_mode="HTML", reply_markup=builder.as_markup())
        elif task.media_type == "audio":
            await callback.message.answer_audio(task.media_id, caption=caption, parse_mode="HTML", reply_markup=builder.as_markup())
        elif task.media_type == "document":
            await callback.message.answer_document(task.media_id, caption=caption, parse_mode="HTML", reply_markup=builder.as_markup())
        elif task.media_type == "video_note":
            await callback.message.answer(caption, parse_mode="HTML", reply_markup=builder.as_markup())
            await callback.message.answer_video_note(task.media_id)
    else:
        await callback.message.answer(caption, parse_mode="HTML", reply_markup=builder.as_markup())

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
        if not row: return await callback.answer("Ошибка, ответ не найден.")
        sub, student, task = row

    await callback.message.delete() 

    text = f"👤 <b>Ответ ученика:</b> {student.first_name} {student.last_name} (@{student.username or 'без_юзернейма'})"
    await callback.message.answer(text, parse_mode="HTML")

    if sub.media_type == "voice": await callback.message.answer_voice(sub.media_id)
    elif sub.media_type == "video_note": await callback.message.answer_video_note(sub.media_id)
    elif sub.media_type == "video": await callback.message.answer_video(sub.media_id)

    await callback.message.answer("Поставь оценку (от 1 до 5) отправив цифру:", reply_markup=get_cancel_t())
    await state.update_data(sub_id=sub.id, task_id=task.id)
    await state.set_state(TeacherCheck.waiting_for_grade)

@teacher_router.message(TeacherCheck.waiting_for_grade, F.text.in_(["1", "2", "3", "4", "5"]))
async def process_grade(message: types.Message, state: FSMContext):
    await state.update_data(grade=int(message.text))
    await message.answer("Теперь напиши комментарий к оценке для ученика:", reply_markup=get_cancel_t())
    await state.set_state(TeacherCheck.waiting_for_comment)

@teacher_router.message(TeacherCheck.waiting_for_comment, F.text)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    async with SessionLocal() as session:
        sub = await session.get(Submission, data['sub_id'])
        sub.grade = data['grade']
        sub.teacher_comment = message.text
        task_id = sub.task_id
        await session.commit()
        
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Вернуться к заданию", callback_data=f"t_chk_t_{task_id}")
    builder.button(text="🏠 В меню", callback_data="t_menu")
    builder.adjust(1)
    
    await message.answer("✅ Оценка и комментарий сохранены!", reply_markup=builder.as_markup())

# ================= 5. СТАТИСТИКА =================
@teacher_router.callback_query(F.data.startswith("t_st_pg_"))
async def stats_groups_list(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    per_page = 5
    
    async with SessionLocal() as session:
        result = await session.execute(select(StudyGroup).where(StudyGroup.teacher_id == callback.from_user.id))
        groups = result.scalars().all()

    if not groups:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ В меню", callback_data="t_menu")
        return await callback.message.edit_text("У вас пока нет созданных групп.", reply_markup=builder.as_markup())

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page*per_page : (page+1)*per_page]

    builder = InlineKeyboardBuilder()
    for g in current_groups:
        builder.button(text=f"📊 {g.class_name} - {g.group_name}", callback_data=f"t_st_g_{g.id}")
    builder.adjust(1)
    
    nav_builder = InlineKeyboardBuilder()
    if page > 0: nav_builder.button(text="⬅️ Пред.", callback_data=f"t_st_pg_{page-1}")
    if page < total_pages - 1: nav_builder.button(text="След. ➡️", callback_data=f"t_st_pg_{page+1}")
    nav_builder.adjust(2)
    builder.attach(nav_builder)
    
    back_builder = InlineKeyboardBuilder()
    back_builder.button(text="🏠 В меню", callback_data="t_menu")
    builder.attach(back_builder)

    await callback.message.edit_text(f"Выберите группу для просмотра статистики (Страница {page+1} из {total_pages}):", reply_markup=builder.as_markup())

@teacher_router.callback_query(F.data.startswith("t_st_g_"))
async def stats_group_details(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    
    async with SessionLocal() as session:
        group = await session.get(StudyGroup, group_id)
        
        # Получаем все задания для этой группы
        result = await session.execute(
            select(Task).where(
                Task.class_name == group.class_name,
                Task.group_name == group.group_name,
                Task.teacher_id == callback.from_user.id
            )
        )
        tasks = result.scalars().all()
        
        text = f"📊 <b>Статистика группы:</b> {group.class_name} - {group.group_name}\n\n"
        total_grades = []
        
        for t in tasks:
            # Получаем все оценки за каждое задание
            sub_res = await session.execute(select(Submission.grade).where(Submission.task_id == t.id, Submission.grade != None))
            grades = sub_res.scalars().all()
            
            if grades:
                avg = sum(grades) / len(grades)
                total_grades.extend(grades)
                text += f"📝 {t.title}: <b>{avg:.1f}</b>\n"
            else:
                text += f"📝 {t.title}: <i>Нет оценок</i>\n"
                
        if total_grades:
            overall_avg = sum(total_grades) / len(total_grades)
            text += f"\n📈 Общий средний балл: <b>{overall_avg:.2f}</b>"
        else:
            text += f"\n📈 Общий средний балл: <i>Нет оценок</i>"

    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Список учеников", callback_data=f"t_st_l_{group_id}")
    builder.button(text="◀️ Назад к группам", callback_data="t_st_pg_0")
    builder.adjust(1)
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())

@teacher_router.callback_query(F.data.startswith("t_st_l_"))
async def stats_student_list(callback: types.CallbackQuery):
    group_id = int(callback.data.split("_")[-1])
    
    async with SessionLocal() as session:
        group = await session.get(StudyGroup, group_id)
        # Ищем учеников в этой группе
        result = await session.execute(
            select(User).where(
                User.class_name == group.class_name,
                User.group_name == group.group_name,
                User.role == "student"
            )
        )
        students = result.scalars().all()

    builder = InlineKeyboardBuilder()
    if not students:
        builder.button(text="◀️ Назад", callback_data=f"t_st_g_{group_id}")
        return await callback.message.edit_text("В этой группе пока нет учеников.", reply_markup=builder.as_markup())

    for s in students:
        builder.button(text=f"👤 {s.first_name} {s.last_name}", callback_data=f"t_st_u_{s.id}_{group_id}")
    builder.adjust(1)
    
    back_builder = InlineKeyboardBuilder()
    back_builder.button(text="◀️ Назад", callback_data=f"t_st_g_{group_id}")
    builder.attach(back_builder)

    await callback.message.edit_text(f"👥 <b>Ученики ({group.class_name} - {group.group_name})</b>\nВыберите ученика:", parse_mode="HTML", reply_markup=builder.as_markup())

@teacher_router.callback_query(F.data.startswith("t_st_u_"))
async def stats_student_details(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    student_id = int(parts[3])
    group_id = int(parts[4])
    
    async with SessionLocal() as session:
        student = await session.get(User, student_id)
        group = await session.get(StudyGroup, group_id)
        
        result = await session.execute(
            select(Task).where(
                Task.class_name == group.class_name,
                Task.group_name == group.group_name,
                Task.teacher_id == callback.from_user.id
            )
        )
        tasks = result.scalars().all()
        
        text = f"👤 <b>Успеваемость:</b> {student.first_name} {student.last_name}\n"
        text += f"🏫 <b>Группа:</b> {group.class_name} - {group.group_name}\n\n"
        
        if not tasks:
            text += "<i>Нет заданий для этой группы.</i>"
        else:
            for t in tasks:
                sub_res = await session.execute(
                    select(Submission).where(
                        Submission.task_id == t.id, 
                        Submission.student_id == student.id
                    )
                )
                sub = sub_res.scalar_one_or_none()
                
                if not sub:
                    text += f"📝 {t.title}: ❌ <i>Не выполнено</i>\n"
                elif sub.grade is None:
                    text += f"📝 {t.title}: ⏳ <i>На проверке</i>\n"
                else:
                    text += f"📝 {t.title}: ⭐️ <b>{sub.grade}</b>\n"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ К списку учеников", callback_data=f"t_st_l_{group_id}")
    builder.adjust(1)
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=builder.as_markup())