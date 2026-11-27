# database/cache.py
"""Слой кэширования Redis для снижения нагрузки на MySQL.

Кэширует часто запрашиваемые данные:
- Профили пользователей (используются в LoggingMiddleware и большинстве хендлеров)
- Списки учебных групп преподавателя и отдельные группы
- Задания для классов/групп и отдельные задания
- Списки учеников в группах
- Список учителей (для админ-панели)
- Рассчитанную статистику по группе

При временной недоступности Redis все операции безопасно откатываются к MySQL.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from typing import Optional
from urllib.parse import quote

from loguru import logger
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import select

import config.config as config
from database.engine import SessionLocal
from database.models import StudyGroup, Task, User

# Асинхронные клиенты Redis: DB 0 — кэш данных, DB 1 — хранилище состояний FSM
redis_cache: Redis = Redis.from_url(
    config.REDIS_CACHE_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

redis_fsm: Redis = Redis.from_url(
    config.REDIS_FSM_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)

DEFAULT_TTL = config.redis_ttl
SHORT_TTL = min(300, config.redis_ttl)


def _key_part(value: str) -> str:
    """Экранирует строковые части ключей Redis (пробелы, двоеточия и т.д.)."""
    return quote(str(value), safe="")


# ================= DTO-МОДЕЛИ ДЛЯ КЭША =================
@dataclass
class CachedUser:
    id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    role: str
    is_banned: bool
    class_name: Optional[str]
    group_name: Optional[str]
    current_streak: int
    last_task_date: Optional[date]
    total_completed: int
    max_tasks_per_day: int
    tasks_today: int

    @classmethod
    def from_orm(cls, user: User) -> "CachedUser":
        return cls(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            is_banned=bool(user.is_banned),
            class_name=user.class_name,
            group_name=user.group_name,
            current_streak=user.current_streak or 0,
            last_task_date=user.last_task_date,
            total_completed=user.total_completed or 0,
            max_tasks_per_day=user.max_tasks_per_day or 0,
            tasks_today=user.tasks_today or 0,
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["last_task_date"] = (
            self.last_task_date.isoformat() if self.last_task_date else None
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "CachedUser":
        raw_date = data.get("last_task_date")
        parsed_date = date.fromisoformat(raw_date) if raw_date else None
        return cls(
            id=data["id"],
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            role=data.get("role", "student"),
            is_banned=bool(data.get("is_banned", False)),
            class_name=data.get("class_name"),
            group_name=data.get("group_name"),
            current_streak=data.get("current_streak", 0),
            last_task_date=parsed_date,
            total_completed=data.get("total_completed", 0),
            max_tasks_per_day=data.get("max_tasks_per_day", 0),
            tasks_today=data.get("tasks_today", 0),
        )


@dataclass
class CachedGroup:
    id: int
    teacher_id: int
    class_name: str
    group_name: str

    @classmethod
    def from_orm(cls, group: StudyGroup) -> "CachedGroup":
        return cls(
            id=group.id,
            teacher_id=group.teacher_id,
            class_name=group.class_name,
            group_name=group.group_name,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CachedGroup":
        return cls(**data)


@dataclass
class CachedTask:
    id: int
    teacher_id: int
    topic: str
    title: str
    description: str
    media_id: Optional[str]
    media_type: Optional[str]
    class_name: str
    group_name: str
    expected_answer: str

    @classmethod
    def from_orm(cls, task: Task) -> "CachedTask":
        return cls(
            id=task.id,
            teacher_id=task.teacher_id,
            topic=task.topic,
            title=task.title,
            description=task.description,
            media_id=task.media_id,
            media_type=task.media_type,
            class_name=task.class_name,
            group_name=task.group_name,
            expected_answer=task.expected_answer,
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CachedTask":
        return cls(**data)


# ================= НИЗКОУРОВНЕВЫЕ ОПЕРАЦИИ С REDIS =================
async def _cache_get(key: str) -> Optional[str]:
    try:
        return await redis_cache.get(key)
    except (RedisError, OSError) as e:
        logger.warning(f"Redis GET failed for {key}: {e}")
        return None


async def _cache_set(key: str, value: str, ttl: int = DEFAULT_TTL) -> None:
    try:
        await redis_cache.set(key, value, ex=ttl)
    except (RedisError, OSError) as e:
        logger.warning(f"Redis SET failed for {key}: {e}")


async def _cache_delete(*keys: str) -> None:
    clean_keys = [k for k in keys if k]
    if not clean_keys:
        return
    try:
        await redis_cache.delete(*clean_keys)
    except (RedisError, OSError) as e:
        logger.warning(f"Redis DEL failed for {clean_keys}: {e}")


async def close_redis() -> None:
    """Корректно закрывает соединения с Redis при остановке бота."""
    for client in (redis_cache, redis_fsm):
        try:
            await client.aclose()
        except Exception:
            pass


# ================= КЛЮЧИ КЭША =================
def _user_key(user_id: int) -> str:
    return f"cache:user:{user_id}"


def _teachers_list_key() -> str:
    return "cache:teachers:list"


def _teacher_groups_key(teacher_id: int) -> str:
    return f"cache:teacher_groups:{teacher_id}"


def _group_key(group_id: int) -> str:
    return f"cache:group:{group_id}"


def _group_students_key(class_name: str, group_name: str) -> str:
    return f"cache:group_students:{_key_part(class_name)}:{_key_part(group_name)}"


def _group_tasks_key(class_name: str, group_name: str) -> str:
    return f"cache:group_tasks:{_key_part(class_name)}:{_key_part(group_name)}"


def _task_key(task_id: int) -> str:
    return f"cache:task:{task_id}"


def _group_stats_key(teacher_id: int, class_name: str, group_name: str) -> str:
    return (
        f"cache:group_stats:{teacher_id}:"
        f"{_key_part(class_name)}:{_key_part(group_name)}"
    )


# ================= ПОЛЬЗОВАТЕЛИ =================
async def get_user_cached(user_id: int) -> Optional[CachedUser]:
    key = _user_key(user_id)
    raw = await _cache_get(key)
    if raw is not None:
        return CachedUser.from_dict(json.loads(raw))

    async with SessionLocal() as session:
        user = await session.get(User, user_id)

    if not user:
        return None

    cached = CachedUser.from_orm(user)
    await _cache_set(key, json.dumps(cached.to_dict(), ensure_ascii=False))
    return cached


async def invalidate_user_cache(
    user_id: int,
    class_name: Optional[str] = None,
    group_name: Optional[str] = None,
    invalidate_teachers: bool = False,
) -> None:
    keys = [_user_key(user_id)]
    if class_name and group_name:
        keys.append(_group_students_key(class_name, group_name))
    if invalidate_teachers:
        keys.append(_teachers_list_key())
    await _cache_delete(*keys)


async def get_teachers_cached() -> list[CachedUser]:
    key = _teachers_list_key()
    raw = await _cache_get(key)
    if raw is not None:
        return [CachedUser.from_dict(item) for item in json.loads(raw)]

    async with SessionLocal() as session:
        teachers = (
            await session.execute(select(User).where(User.role.in_(["teacher", "admin", "founder"])))
        ).scalars().all()

    cached_list = [CachedUser.from_orm(t) for t in teachers]
    await _cache_set(
        key,
        json.dumps([u.to_dict() for u in cached_list], ensure_ascii=False),
        ttl=SHORT_TTL,
    )
    return cached_list


async def invalidate_teachers_cache() -> None:
    await _cache_delete(_teachers_list_key())


# ================= УЧЕБНЫЕ ГРУППЫ =================
async def get_teacher_groups_cached(teacher_id: int) -> list[CachedGroup]:
    key = _teacher_groups_key(teacher_id)
    raw = await _cache_get(key)
    if raw is not None:
        return [CachedGroup.from_dict(item) for item in json.loads(raw)]

    async with SessionLocal() as session:
        groups = (
            await session.execute(
                select(StudyGroup).where(StudyGroup.teacher_id == teacher_id)
            )
        ).scalars().all()

    cached_list = [CachedGroup.from_orm(g) for g in groups]
    await _cache_set(
        key, json.dumps([g.to_dict() for g in cached_list], ensure_ascii=False)
    )
    return cached_list


async def invalidate_teacher_groups_cache(teacher_id: int) -> None:
    await _cache_delete(_teacher_groups_key(teacher_id))


async def get_group_cached(group_id: int) -> Optional[CachedGroup]:
    key = _group_key(group_id)
    raw = await _cache_get(key)
    if raw is not None:
        return CachedGroup.from_dict(json.loads(raw))

    async with SessionLocal() as session:
        group = await session.get(StudyGroup, group_id)

    if not group:
        return None

    cached = CachedGroup.from_orm(group)
    await _cache_set(key, json.dumps(cached.to_dict(), ensure_ascii=False))
    return cached


async def get_group_students_cached(
    class_name: str, group_name: str
) -> list[CachedUser]:
    key = _group_students_key(class_name, group_name)
    raw = await _cache_get(key)
    if raw is not None:
        return [CachedUser.from_dict(item) for item in json.loads(raw)]

    async with SessionLocal() as session:
        students = (
            await session.execute(
                select(User).where(
                    User.class_name == class_name,
                    User.group_name == group_name,
                    User.role == "student",
                )
            )
        ).scalars().all()

    cached_list = [CachedUser.from_orm(s) for s in students]
    await _cache_set(
        key,
        json.dumps([s.to_dict() for s in cached_list], ensure_ascii=False),
        ttl=SHORT_TTL,
    )
    return cached_list


async def invalidate_group_students_cache(class_name: str, group_name: str) -> None:
    if class_name and group_name:
        await _cache_delete(_group_students_key(class_name, group_name))


# ================= ЗАДАНИЯ =================
async def get_group_tasks_cached(
    class_name: str, group_name: str, teacher_id: Optional[int] = None
) -> list[CachedTask]:
    key = _group_tasks_key(class_name, group_name)
    raw = await _cache_get(key)
    if raw is not None:
        tasks = [CachedTask.from_dict(item) for item in json.loads(raw)]
    else:
        async with SessionLocal() as session:
            db_tasks = (
                await session.execute(
                    select(Task)
                    .where(
                        Task.class_name == class_name,
                        Task.group_name == group_name,
                    )
                    .order_by(Task.id)
                )
            ).scalars().all()
        tasks = [CachedTask.from_orm(t) for t in db_tasks]
        await _cache_set(
            key, json.dumps([t.to_dict() for t in tasks], ensure_ascii=False)
        )

    if teacher_id is not None:
        return [t for t in tasks if t.teacher_id == teacher_id]
    return tasks


async def invalidate_group_tasks_cache(class_name: str, group_name: str) -> None:
    if class_name and group_name:
        await _cache_delete(_group_tasks_key(class_name, group_name))


async def get_task_cached(task_id: int) -> Optional[CachedTask]:
    key = _task_key(task_id)
    raw = await _cache_get(key)
    if raw is not None:
        return CachedTask.from_dict(json.loads(raw))

    async with SessionLocal() as session:
        task = await session.get(Task, task_id)

    if not task:
        return None

    cached = CachedTask.from_orm(task)
    await _cache_set(key, json.dumps(cached.to_dict(), ensure_ascii=False))
    return cached


async def invalidate_tasks_cache(task_ids: list[int]) -> None:
    if task_ids:
        await _cache_delete(*[_task_key(tid) for tid in task_ids])


# ================= СТАТИСТИКА ГРУППЫ =================
async def get_group_stats_cached(
    teacher_id: int, class_name: str, group_name: str
) -> Optional[str]:
    return await _cache_get(_group_stats_key(teacher_id, class_name, group_name))


async def set_group_stats_cached(
    teacher_id: int, class_name: str, group_name: str, text: str
) -> None:
    await _cache_set(
        _group_stats_key(teacher_id, class_name, group_name), text, ttl=SHORT_TTL
    )


async def invalidate_group_stats_cache(
    teacher_id: int, class_name: str, group_name: str
) -> None:
    if class_name and group_name:
        await _cache_delete(_group_stats_key(teacher_id, class_name, group_name))
