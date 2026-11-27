# webapp/routers/admin.py
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

import config.config as config
from database.cache import CachedUser, invalidate_user_cache
from database.engine import SessionLocal
from database.models import StudyGroup, Submission, Task, User
from webapp.dependencies import get_current_user, require_roles
from webapp.schemas import AdminUserUpdateRequest

router = APIRouter(prefix="/api/admin", tags=["admin"])
ADMIN_ROLES = ("admin", "founder")


@router.get("/overview")
async def api_admin_overview(user: CachedUser = Depends(get_current_user)):
    require_roles(user, ADMIN_ROLES)
    async with SessionLocal() as session:
        users = (await session.execute(select(User).order_by(User.id))).scalars().all()
        groups_count = (
            await session.execute(select(func.count(StudyGroup.id)))
        ).scalar() or 0
        tasks_count = (
            await session.execute(select(func.count(Task.id)))
        ).scalar() or 0
        subs_count = (
            await session.execute(select(func.count(Submission.id)))
        ).scalar() or 0

    role_counts: dict[str, int] = defaultdict(int)
    for u in users:
        role_counts[u.role] += 1

    return {
        "counts": {
            "users": len(users),
            "students": role_counts["student"],
            "teachers": role_counts["teacher"],
            "admins": role_counts["admin"],
            "founders": role_counts["founder"],
            "groups": groups_count,
            "tasks": tasks_count,
            "submissions": subs_count,
        },
        "users": [CachedUser.from_orm(u).to_dict() for u in users],
    }


@router.patch("/users/{target_id}")
async def api_admin_update_user(
    target_id: int,
    payload: AdminUserUpdateRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ADMIN_ROLES)
    is_founder = user.role == "founder" or user.id in config.FOUNDERS_ID

    async with SessionLocal() as session:
        target = await session.get(User, target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Пользователь не найден.")
        if target.role == "founder":
            raise HTTPException(
                status_code=403,
                detail="Нельзя изменять или блокировать пользователя с ролью FOUNDER.",
            )

        old_class, old_group = target.class_name, target.group_name
        role_changed = False

        if payload.role is not None:
            if (payload.role == "admin" or target.role == "admin") and not is_founder:
                raise HTTPException(
                    status_code=403,
                    detail="Назначать и снимать администраторов может только FOUNDER.",
                )
            target.role = payload.role
            role_changed = True

        if payload.is_banned is not None:
            if target.role == "admin" and not is_founder:
                raise HTTPException(
                    status_code=403,
                    detail="Блокировать администратора может только FOUNDER.",
                )
            target.is_banned = payload.is_banned

        if payload.unlink_group:
            target.class_name = None
            target.group_name = None

        await session.commit()
        updated = CachedUser.from_orm(target).to_dict()

    await invalidate_user_cache(
        target_id,
        old_class,
        old_group,
        invalidate_teachers=role_changed,
    )
    return {"ok": True, "user": updated}
