# handlers/admin.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from config import ADMINS_ID
from database.engine import SessionLocal
from database.models import User
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
    builder.button(text="🔨 Забанить", callback_data="admin_ban")
    builder.button(text="🕊 Разбанить", callback_data="admin_unban")
    builder.adjust(2, 1, 2)

    text = "<b>🛠 Панель администратора</b>\nВыберите действие:"
    if is_edit:
        await message.edit_text(
            text, parse_mode="HTML", reply_markup=builder.as_markup()
        )
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=builder.as_markup())

# Фильтр убран. Теперь /admin работает везде и всегда!
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

    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=builder.as_markup()
    )

@admin_router.callback_query(F.data.startswith("admin_"))
async def admin_callbacks(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    if action == "admin_add_teacher":
        await callback.message.edit_text(
            "Введите @юзернейм пользователя для назначения учителем:",
            reply_markup=get_cancel_admin(),
        )
        await state.set_state(AdminPanel.waiting_for_username_teacher)
    elif action == "admin_rem_teacher":
        await callback.message.edit_text(
            "Введите @юзернейм для снятия роли учителя:",
            reply_markup=get_cancel_admin(),
        )
        await state.set_state(AdminPanel.waiting_for_username_remove)
    elif action == "admin_ban":
        await callback.message.edit_text(
            "Введите @юзернейм для бана:", reply_markup=get_cancel_admin()
        )
        await state.set_state(AdminPanel.waiting_for_username_ban)
    elif action == "admin_unban":
        await callback.message.edit_text(
            "Введите @юзернейм для разбана:", reply_markup=get_cancel_admin()
        )
        await state.set_state(AdminPanel.waiting_for_username_unban)
    await callback.answer()

async def update_user_by_username(
    message: types.Message, state: FSMContext, field: str, value
):
    username = message.text.replace("@", "")
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                f"❌ Пользователь @{username} не найден. Он должен нажать /start."
            )
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