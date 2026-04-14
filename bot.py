import asyncio
import os
import logging
import graypy
from loguru import logger
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, types, BaseMiddleware
from aiogram.filters import Command
from aiogram.types import BotCommand, TelegramObject, Update
from aiogram.client.session.aiohttp import AiohttpSession

import config.config as config
from database.engine import SessionLocal
from database.models import User

from handlers.admin import admin_router
from handlers.student import student_router
from handlers.teacher import teacher_router

# ================= НАСТРОЙКА ЛОГОВ =================

if not os.path.exists("log"):
    os.makedirs("log")

logger.remove() # Убираем дефолтный вывод в консоль
logger.add("log/bot.log", rotation="10 MB", retention="10 days", level="INFO", 
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")

# Интеграция Loguru с Graylog
if config.graylog_host:
    try:
        # Создаем скрытый стандартный логгер специально для отправки GELF
        gelf_logger = logging.getLogger("gelf_logger")
        gelf_logger.setLevel(logging.INFO)
        handler = graypy.GELFUDPHandler(config.graylog_host, config.graylog_port)
        gelf_logger.addHandler(handler)

        # Мост между Loguru и Graypy
        def graylog_sink(message):
            record = message.record
            # Передаем текст лога и распаковываем .bind() поля, чтобы Graylog их увидел
            gelf_logger.info(message, extra=record["extra"])

        # Добавляем мост в Loguru
        logger.add(graylog_sink, level="INFO")
        logger.info("📡 Подключение к Graylog через Loguru успешно настроено!")
    except Exception as e:
        print(f"❌ Ошибка Graylog: {e}")

# ================= СЛОВАРЬ ПЕРЕВОДА КНОПОК =================
def translate_cb(data: str) -> str:
    actions = {
        "s_panel": "Выход в меню",
        "s_profile": "Профиль",
        "s_tasks_new": "Новые темы",
        "s_tasks_progress": "В процессе",
        "s_completed": "Выполненные",
        "s_edit_name": "Смена имени",
        "reg_confirm": "Регистрация: Да",
        "reg_edit": "Регистрация: Изменить",
        "ans_send": "Отправка ответа",
        "ans_retry": "Перезапись",
        "t_menu": "Меню учителя",
        "t_new_task": "Создать задание",
        "t_del_task_start": "Удаление задания",
        "t_resume_draft": "К черновику",
        "t_check_tasks_0": "Проверка ответов",
        "t_chkd_pg_0": "Проверенные работы",
        "t_lc_pg_0": "Список классов",
        "t_st_pg_0": "Статистика",
        "t_add_group": "Создать группу",
        "t_add_student": "Добавить ученика",
        "t_rem_student": "Удалить ученика",
        "confirm_task": "Опубликовать тему",
        "admin_back": "Админ-панель",
        "admin_add_teacher": "Назначить учителя",
        "admin_rem_teacher": "Разжаловать учителя",
        "admin_broad_student": "Рассылка ученикам",
        "admin_broad_teacher": "Рассылка учителям",
        "admin_pml_0": "Личные сообщения",
        "adm_actl_0": "История действий",
        "adm_unl_0": "Отвязать от группы",
        "admin_ban": "Бан",
        "admin_unban": "Разбан",
    }
    if data.startswith("s_sub_"): return "Детали ответа"
    if data.startswith("s_do_t_"): return "Начать задание"
    if data.startswith("tg_group_"): return "Выбор группы"
    if data.startswith("t_chk_t_"): return "Выбор задания для проверки"
    if data.startswith("t_chk_s_"): return "Проверка ответа конкретного ученика"
    if data.startswith("adms_"): return "Профиль пользователя (админ)"
    if data.startswith("adm_actu_"): return "Просмотр истории действий"
    return actions.get(data, "Нажатие кнопки")

# ================= MIDDLEWARE =================
class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self, 
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], 
        event: Update, 
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            async with SessionLocal() as session:
                db_user = await session.get(User, user.id)
                role = db_user.role if db_user else "new_user"
                name = f"{db_user.first_name} {db_user.last_name}" if db_user and db_user.first_name else f"{user.first_name} {user.last_name or ''}"

            name = name.strip() or "Без_имени"
            username = f"(@{user.username})" if user.username else "(@None)"
            
            # Привязываем переменные к логгеру (чтобы в Graylog были удобные фильтры слева)
            context_logger = logger.bind(
                tg_user_id=user.id,
                tg_username=user.username or "None",
                tg_role=role,
                tg_name=name
            )

            # Формируем строку в точном соответствии с требуемым шаблоном
            if event.message:
                msg_text = event.message.text or "Медиа/Файл"
                log_msg = f"[СООБЩЕНИЕ] | {name} {username} | role: {role} | {msg_text}"
                context_logger.info(log_msg)
                
            elif event.callback_query:
                cb_data = event.callback_query.data
                translated = translate_cb(cb_data)
                log_msg = f"[КНОПКА] | {name} {username} | role: {role} | {cb_data} ({translated})"
                context_logger.info(log_msg)
                
        return await handler(event, data)


# ================= ЗАПУСК =================
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="menu", description="Главное меню"),
        BotCommand(command="profile", description="Мой профиль (для ученика)"),
        BotCommand(command="admin", description="Панель администратора")
    ]
    await bot.set_my_commands(commands)

async def main():
    if config.proxy_host:
        proxy = f"http://{config.proxy_login}:{config.proxy_password}@{config.proxy_host}:{config.proxy_port}"
        session = AiohttpSession(proxy=proxy)
    else:
        session = None
        
    bot = Bot(token=config.BOT_TOKEN, session=session)
    dp = Dispatcher()
    dp.update.middleware(LoggingMiddleware())
    
    dp.include_router(admin_router)
    dp.include_router(student_router)
    dp.include_router(teacher_router)
    
    await set_bot_commands(bot)
    logger.info("🚀 Бот запущен!")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())