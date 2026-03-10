# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from config import ADMIN_ID
from database.engine import SessionLocal
from database.models import User
from states.states import AdminPanel

admin_router = Router()

@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ У вас нет прав администратора.")
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Назначить учителя", callback_data="admin_add_teacher")
    builder.button(text="➖ Убрать учителя", callback_data="admin_rem_teacher")
    builder.button(text="🔨 Забанить", callback_data="admin_ban")
    builder.button(text="🕊 Разбанить", callback_data="admin_unban")
    builder.adjust(2)
    
    await message.answer(
        "<b>🛠 Панель администратора</b>\nВыберите действие:", 
        parse_mode="HTML", 
        reply_markup=builder.as_markup()
    )

# Обработка нажатий на кнопки админки
@admin_router.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    if action == "admin_add_teacher":
        await callback.message.answer("Введите @юзернейм пользователя для назначения учителем:")
        await state.set_state(AdminPanel.waiting_for_username_teacher)
    elif action == "admin_rem_teacher":
        await callback.message.answer("Введите @юзернейм для снятия роли учителя:")
        await state.set_state(AdminPanel.waiting_for_username_remove)
    elif action == "admin_ban":
        await callback.message.answer("Введите @юзернейм для бана:")
        await state.set_state(AdminPanel.waiting_for_username_ban)
    elif action == "admin_unban":
        await callback.message.answer("Введите @юзернейм для разбана:")
        await state.set_state(AdminPanel.waiting_for_username_unban)
    await callback.answer()

# Универсальная функция для поиска и обновления пользователя по юзернейму
async def update_user_by_username(message: types.Message, state: FSMContext, field: str, value):
    # Очищаем юзернейм от символа '@' если он есть
    username = message.text.replace("@", "")
    
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(f"❌ Пользователь @{username} не найден. Он должен сначала нажать /start в боте.")
        else:
            setattr(user, field, value)
            await session.commit()
            await message.answer(f"✅ Данные пользователя @{username} успешно обновлены!")
            
    await state.clear()

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