# middlewares/registration.py
"""Middleware для проверки регистрации и блокировки пользователя."""

from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, TelegramObject

from database.cache import get_user_cached
from lexicon import LEXICON


class RegistrationCheckMiddleware(BaseMiddleware):
    """Блокирует любые команды и действия незарегистрированных пользователей.

    Пропускает только команду /start и шаги активной регистрации (Registration:*).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any],
    ) -> Any:
        # 1. Команда /start всегда разрешена
        if isinstance(event, Message) and event.text:
            if event.text.strip().split()[0].split("@")[0] == "/start":
                return await handler(event, data)

        # 2. Шаги текущей регистрации (выбор роли, имя, фамилия, подтверждение) разрешены
        state: FSMContext | None = data.get("state")
        if state is not None:
            current_state = await state.get_state()
            if current_state and current_state.startswith("Registration:"):
                return await handler(event, data)

        # 3. Проверяем наличие пользователя в Redis/MySQL и завершённость регистрации
        tg_user = event.from_user
        if not tg_user:
            return await handler(event, data)

        db_user = await get_user_cached(tg_user.id)
        if not db_user or not db_user.first_name or not db_user.last_name:
            if isinstance(event, Message):
                await event.answer(LEXICON["not_registered"], parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer(LEXICON["not_registered_alert"], show_alert=True)
                if event.message:
                    await event.message.answer(
                        LEXICON["not_registered"], parse_mode="HTML"
                    )
            return

        # 4. Проверяем блокировку пользователя
        if db_user.is_banned:
            if isinstance(event, Message):
                await event.answer(LEXICON["user_banned"])
            elif isinstance(event, CallbackQuery):
                await event.answer(LEXICON["user_banned"], show_alert=True)
            return

        return await handler(event, data)
