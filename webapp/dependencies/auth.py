# webapp/dependencies/auth.py
"""Зависимости аутентификации и проверки ролей для FastAPI."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status

import config.config as config
from database.cache import CachedUser, get_user_cached


def verify_telegram_init_data(init_data: str, bot_token: str) -> dict[str, Any]:
    """Валидирует подпись initData от Telegram Mini App (HMAC-SHA256)."""
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствуют данные авторизации Telegram (initData).",
        )

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный формат initData: отсутствует hash.",
        )

    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items(), key=lambda item: item[0])
    )
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256
    ).digest()
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительная подпись Telegram initData.",
        )

    raw_user = parsed.get("user")
    if not raw_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="В initData отсутствуют данные пользователя.",
        )

    try:
        return json.loads(raw_user)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ошибка разбора данных пользователя в initData.",
        ) from exc


async def get_current_user(
    x_telegram_init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> CachedUser:
    """Возвращает авторизованного пользователя из Redis-кэша или MySQL."""
    if x_telegram_init_data:
        tg_user = verify_telegram_init_data(x_telegram_init_data, config.BOT_TOKEN)
        user_id = int(tg_user["id"])
    elif config.WEBAPP_DEV_USER_ID.isdigit():
        user_id = int(config.WEBAPP_DEV_USER_ID)
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Откройте приложение через кнопку внутри Telegram-бота.",
        )

    user = await get_user_cached(user_id)
    if not user or not user.first_name or not user.last_name:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не зарегистрированы. Пройдите регистрацию через /start в боте.",
        )
    if user.is_banned:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ваш аккаунт заблокирован администратором.",
        )
    return user


def require_roles(user: CachedUser, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения этого действия.",
        )
