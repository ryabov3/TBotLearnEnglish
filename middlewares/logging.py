# middlewares/logging.py
"""Middleware для логирования всех входящих сообщений и нажатий кнопок."""

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from loguru import logger

from database.cache import get_user_cached
from lexicon import LEXICON_CALLBACKS, LEXICON_CALLBACK_PREFIXES


def translate_cb(data: str) -> str:
    for prefix, label in LEXICON_CALLBACK_PREFIXES:
        if data.startswith(prefix):
            return label
    return LEXICON_CALLBACKS.get(data, "Нажатие кнопки")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            db_user = await get_user_cached(user.id)
            role = db_user.role if db_user else "new_user"
            name = (
                f"{db_user.first_name} {db_user.last_name}"
                if db_user and db_user.first_name
                else f"{user.first_name} {user.last_name or ''}"
            )

            name = name.strip() or "Без_имени"
            username = f"(@{user.username})" if user.username else "(@None)"

            context_logger = logger.bind(
                tg_user_id=user.id,
                tg_username=user.username or "None",
                tg_role=role,
                tg_name=name,
            )

            if event.message:
                msg_text = event.message.text or "Медиа/Файл"
                log_msg = f"[СООБЩЕНИЕ] | {name} {username} | role: {role} | {msg_text}"
                context_logger.info(log_msg)

            elif event.callback_query:
                cb_data = event.callback_query.data or ""
                translated = translate_cb(cb_data)
                log_msg = (
                    f"[КНОПКА] | {name} {username} | role: {role} | "
                    f"{cb_data} ({translated})"
                )
                context_logger.info(log_msg)

        return await handler(event, data)
