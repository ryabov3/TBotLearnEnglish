# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import BotCommand
import config

from handlers.admin import admin_router
from handlers.student import student_router
from handlers.teacher import teacher_router

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="menu", description="Открыть панель управления"),
        BotCommand(command="profile", description="Мой профиль (для ученика)"),
        BotCommand(command="admin", description="Панель администратора")
    ]
    await bot.set_my_commands(commands)

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # --- ТЕСТОВАЯ КОМАНДА (Без базы данных) ---
    @dp.message(Command("ping"))
    async def cmd_ping(message: types.Message):
        await message.answer("🏓 Pong! Я жив, связь с Telegram работает!")
    
    dp.include_router(admin_router)
    dp.include_router(student_router)
    dp.include_router(teacher_router)
    
    await set_bot_commands(bot)
    
    print("🚀 Бот запущен! Ожидаю команды...")
    
    # ВАЖНО: Эта строчка удалит все старые команды, 
    # на которых бот мог зависнуть, пока был выключен
    await bot.delete_webhook(drop_pending_updates=True)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())