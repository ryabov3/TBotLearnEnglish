# filters/role.py
"""Пользовательские фильтры ролей для роутеров aiogram.

Иерархия ролей: student < teacher < admin < founder.
"""

from typing import Iterable, Union

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from config.config import ADMINS_ID, FOUNDERS_ID
from database.cache import get_user_cached


class RoleFilter(BaseFilter):
    """Проверяет, что роль пользователя в БД/кэше входит в разрешённый список."""

    def __init__(self, roles: Union[str, Iterable[str]]) -> None:
        if isinstance(roles, str):
            self.roles = {roles}
        else:
            self.roles = set(roles)

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        if not event.from_user:
            return False
        user = await get_user_cached(event.from_user.id)
        return bool(user and not user.is_banned and user.role in self.roles)


class IsFounderFilter(BaseFilter):
    """Пропускает только пользователей с ролью founder (или из FOUNDERS_ID)."""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        if not event.from_user:
            return False
        if event.from_user.id in FOUNDERS_ID:
            return True
        user = await get_user_cached(event.from_user.id)
        return bool(user and not user.is_banned and user.role == "founder")


class IsAdminFilter(BaseFilter):
    """Пропускает пользователей с ролью admin и выше (admin, founder)."""

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        if not event.from_user:
            return False
        if event.from_user.id in FOUNDERS_ID or event.from_user.id in ADMINS_ID:
            return True
        user = await get_user_cached(event.from_user.id)
        return bool(user and not user.is_banned and user.role in ("admin", "founder"))


class IsTeacherFilter(RoleFilter):
    """Пропускает учителей, администраторов и основателей."""

    def __init__(self) -> None:
        super().__init__(roles=("teacher", "admin", "founder"))


class IsStudentFilter(RoleFilter):
    """Пропускает учеников."""

    def __init__(self) -> None:
        super().__init__(roles=("student",))
