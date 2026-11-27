import asyncio
import logging
import os
import sys

import graypy
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand
from loguru import logger

import config.config as config
from database.cache import close_redis, redis_fsm
from handlers.admin import admin_router
from handlers.student import student_router
from handlers.teacher import teacher_router
from lexicon import LEXICON
from middlewares import LoggingMiddleware, RegistrationCheckMiddleware

# ================= НАСТРОЙКА ЛОГОВ =================

if not os.path.exists("log"):
    os.makedirs("log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)
logger.add(
    "log/bot.log",
    rotation="10 MB",
    retention="10 days",
    level="INFO",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

# Интеграция Loguru с Graylog
if config.graylog_host:
    try:
        gelf_logger = logging.getLogger("gelf_logger")
        gelf_logger.setLevel(logging.INFO)
        handler = graypy.GELFUDPHandler(config.graylog_host, config.graylog_port)
        gelf_logger.addHandler(handler)

        def graylog_sink(message):
            record = message.record
            gelf_logger.info(message, extra=record["extra"])

        logger.add(graylog_sink, level="INFO")
        logger.info("📡 Подключение к Graylog через Loguru успешно настроено!")
    except Exception as e:
        print(f"❌ Ошибка Graylog: {e}")


# ================= ЗАПУСК =================
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description=LEXICON["cmd_start_desc"]),
    ]
    await bot.set_my_commands(commands)


async def main():
    if config.proxy_host:
        proxy = (
            f"http://{config.proxy_login}:{config.proxy_password}"
            f"@{config.proxy_host}:{config.proxy_port}"
        )
        session = AiohttpSession(proxy=proxy)
    else:
        session = None

    bot = Bot(token=config.BOT_TOKEN, session=session)

    try:
        await redis_fsm.ping()
        storage = RedisStorage(redis=redis_fsm)
        logger.info(
            "⚡ Redis подключен: используется RedisStorage для FSM и кэш запросов к MySQL."
        )
    except Exception as e:
        logger.warning(
            f"⚠️ Redis недоступен при старте ({e}), используется MemoryStorage для FSM."
        )
        storage = MemoryStorage()

    dp = Dispatcher(storage=storage)

    # Логирование всех апдейтов и проверка регистрации на каждом сообщении/кнопке
    dp.update.middleware(LoggingMiddleware())
    dp.message.outer_middleware(RegistrationCheckMiddleware())
    dp.callback_query.outer_middleware(RegistrationCheckMiddleware())

    dp.include_router(admin_router)
    dp.include_router(student_router)
    dp.include_router(teacher_router)

    await set_bot_commands(bot)
    logger.info("🚀 Бот запущен!")

    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await close_redis()


if __name__ == "__main__":
    asyncio.run(main())
