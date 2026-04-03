import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.client.session.aiohttp import AiohttpSession
import config

async def main():
    logging.basicConfig(level=logging.INFO)
    
    proxy = f"http://{config.proxy_login}:{config.proxy_password}@{config.proxy_host}:{config.proxy_port}"
    session = AiohttpSession(proxy=proxy)
    bot = Bot(token=config.BOT_TOKEN, session=session)
    dp = Dispatcher()

    @dp.message(CommandStart())
    async def cmd_test_start(message: types.Message):
        print("✅ Команда /start получена!")
        await message.answer("🔥 УРА! Бот успешно работает и умеет отправлять сообщения!")

    @dp.message()
    async def echo_all(message: types.Message):
        print(f"✅ Получен текст: {message.text}")
        await message.answer(f"Ты написал: {message.text}")

    print("🛠 Тестовый бот запущен. Напиши ему /start...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())