# filters/name.py
"""Фильтр и утилиты валидации имени и фамилии."""

import re

from aiogram.filters import BaseFilter
from aiogram.types import Message

NAME_PATTERN = re.compile(r"^[А-ЯЁа-яёA-Za-z]+(?:-[А-ЯЁа-яёA-Za-z]+)?$")
MIN_NAME_LEN = 2
MAX_NAME_LEN = 50


def is_valid_name(value: str | None) -> bool:
    """Проверяет, что имя/фамилия состоит только из букв (допустим один дефис) и длиной 2–50 символов."""
    if not value:
        return False
    cleaned = value.strip()
    if not (MIN_NAME_LEN <= len(cleaned) <= MAX_NAME_LEN):
        return False
    return bool(NAME_PATTERN.fullmatch(cleaned))


def normalize_name(value: str) -> str:
    """Приводит имя/фамилию к аккуратному виду (с заглавной буквы, учитывая дефис)."""
    cleaned = value.strip()
    return "-".join(part.capitalize() for part in cleaned.split("-"))


class ValidNameFilter(BaseFilter):
    """Пропускает текстовые сообщения с корректным именем или фамилией."""

    async def __call__(self, message: Message) -> bool:
        return bool(message.text and is_valid_name(message.text))
