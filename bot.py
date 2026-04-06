import asyncio
import os
from loguru import logger
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import BotCommand, TelegramObject, Update
from aiogram.client.session.aiohttp import AiohttpSession

import config
from database.engine import SessionLocal
from database.models import User

from handlers.admin import admin_router
from handlers.student import student_router
from handlers.teacher import teacher_router

# ================= НАСТРОЙКА ЛОГОВ =================
if not os.path.exists("log"):
    os.makedirs("log")

logger.add("log/bot.log", rotation="10 MB", retention="10 days", level="INFO", 
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self, 
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], 
        event: Update, 
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            # Получаем роль пользователя для логов
            async with SessionLocal() as session:
                db_user = await session.get(User, user.id)
                role = db_user.role if db_user else "new_user"

            if event.message:
                text = event.message.text or "Медиа/Файл"
                logger.info(f"[СООБЩЕНИЕ] ID:{user.id} (@{user.username}) | Роль: {role} | Текст: {text}")
            elif event.callback_query:
                logger.info(f"[КНОПКА] ID:{user.id} (@{user.username}) | Роль: {role} | Кликнул: {event.callback_query.data}")
                
        return await handler(event, data)


# ================= ОСНОВНОЙ КОД БОТА =================
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Нажмите старт, чтобы начать"),
        BotCommand(command="menu", description="Открыть панель управления"),
        BotCommand(command="profile", description="Мой профиль (для ученика)"),
        BotCommand(command="admin", description="Панель администратора")
    ]
    await bot.set_my_commands(commands)

async def main():
    proxy = (
        f"http://{config.proxy_login}:{config.proxy_password}@"
        f"{config.proxy_host}:{config.proxy_port}"
    )
    session = AiohttpSession(proxy=proxy)
    bot = Bot(token=config.BOT_TOKEN, session=session)
    dp = Dispatcher()
    
    # Подключаем middleware для логов ко всем обновлениям
    dp.update.middleware(LoggingMiddleware())
    
    @dp.message(Command("ping"))
    async def cmd_ping(message: types.Message):
        await message.answer("🏓 Pong! Я жив, связь с Telegram работает!")
    
    dp.include_router(admin_router)
    dp.include_router(student_router)
    dp.include_router(teacher_router)
    
    await set_bot_commands(bot)
    
    logger.info("🚀 Бот успешно запущен! Ожидаю команды...")
    print("🚀 Бот запущен! Логи пишутся в терминал и папку log/")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())