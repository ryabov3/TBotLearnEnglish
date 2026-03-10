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

async def is_teacher(user_id: int) -> bool:
    async with SessionLocal() as session:
        user = await session.get(User, user_id)
        return user and user.role in ["teacher", "admin"]

# ================= ПАНЕЛЬ УЧИТЕЛЯ (Только возврат в меню) =================
# Саму команду /menu мы перенесли в student.py, чтобы она была универсальной для всех

@teacher_router.callback_query(F.data == "t_menu")
async def teacher_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать задание", callback_data="t_new_task")
    builder.button(text="✅ Проверить ответы", callback_data="t_check_tasks")
    builder.button(text="➕ Создать группу", callback_data="t_add_group")
    builder.button(text="👤 Добавить ученика", callback_data="t_add_student")
    builder.adjust(1)
    await callback.message.edit_text("👨‍🏫 <b>Панель Учителя</b>\nВыберите действие:", parse_mode="HTML", reply_markup=builder.as_markup())

# ================= 1. СОЗДАНИЕ ГРУППЫ =================
@teacher_router.callback_query(F.data == "t_add_group")
async def start_add_group(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введи название класса (например, 5А):")
    await state.set_state(TeacherGroup.class_name)

@teacher_router.message(TeacherGroup.class_name, F.text)
async def process_class_name(message: types.Message, state: FSMContext):
    await state.update_data(class_name=message.text)
    await message.answer("Введи название группы (например, Группа 1):")
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
        
    await callback.message.edit_text(f"Группа выбрана ({group.class_name} - {group.group_name}).\nТеперь отправьте @юзернейм ученика:")
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
    await callback.message.edit_text("Введи название темы (например, 'Хобби - Спорт'):")
    await state.set_state(TeacherTask.title)

@teacher_router.message(TeacherTask.title, F.text)
async def task_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Напиши текстовое описание задания:")
    await state.set_state(TeacherTask.description)

@teacher_router.message(TeacherTask.description, F.text)
async def task_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭ Пропустить медиа", callback_data="skip_media")
    
    await message.answer(
        "Отправь файл с примером (Фото, Видео, Аудио, Голосовое или Кружок).\n"
        "Если медиа не нужно, нажми «Пропустить».",
        reply_markup=builder.as_markup()
    )
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

    await state.update_data(media_id=media_id, media_type=media_type)
    await ask_for_groups(message, state, message.from_user.id)

async def ask_for_groups(message_or_callback: types.Message, state: FSMContext, teacher_id: int):
    data = await state.get_data()
    if 'selected_group_ids' not in data:
        await state.update_data(selected_group_ids=[])
        selected = []
    else:
        selected = data['selected_group_ids']

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
    builder.adjust(1)

    text = "Выбери классы и группы для этого задания (можно несколько) и нажми 'Отправить':"
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
    selected_ids = data.get('selected_group_ids', [])
    
    if not selected_ids:
        return await callback.answer("❗ Выберите хотя бы одну группу!", show_alert=True)
        
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
@teacher_router.callback_query(F.data == "t_check_tasks")
async def check_tasks(callback: types.CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        result = await session.execute(
            select(Submission, Task, User)
            .join(Task, Submission.task_id == Task.id)
            .join(User, Submission.student_id == User.id)
            .where(Task.teacher_id == callback.from_user.id, Submission.grade == None)
        )
        row = result.first()
        
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ В меню", callback_data="t_menu")
        
        if not row:
            return await callback.message.edit_text("✅ Отличная работа! Непроверенных заданий нет.", reply_markup=builder.as_markup())
            
        sub, task, student = row
        
        await callback.message.delete()
        
        await callback.message.answer(
            f"📚 <b>Задание:</b> {task.title}\n"
            f"👤 <b>Ученик:</b> @{student.username or 'Без_имени'}\n\n"
            f"Слушаем ответ ученика:", 
            parse_mode="HTML"
        )
        
        if sub.media_type == "voice":
            await callback.message.answer_voice(sub.media_id)
        elif sub.media_type == "video_note":
            await callback.message.answer_video_note(sub.media_id)
        elif sub.media_type == "video":
            await callback.message.answer_video(sub.media_id)
        
        await callback.message.answer("Поставь оценку (от 1 до 5) отправив цифру:")
        await state.update_data(sub_id=sub.id)
        await state.set_state(TeacherCheck.waiting_for_grade)

@teacher_router.message(TeacherCheck.waiting_for_grade, F.text.in_(["1", "2", "3", "4", "5"]))
async def process_grade(message: types.Message, state: FSMContext):
    await state.update_data(grade=int(message.text))
    await message.answer("Теперь напиши комментарий к оценке для ученика:")
    await state.set_state(TeacherCheck.waiting_for_comment)

@teacher_router.message(TeacherCheck.waiting_for_comment, F.text)
async def process_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    async with SessionLocal() as session:
        sub = await session.get(Submission, data['sub_id'])
        sub.grade = data['grade']
        sub.teacher_comment = message.text
        await session.commit()
        
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Проверить следующее ➡️", callback_data="t_check_tasks")
    builder.button(text="◀️ В меню", callback_data="t_menu")
    builder.adjust(1)
    
    await message.answer("✅ Оценка и комментарий сохранены!", reply_markup=builder.as_markup())