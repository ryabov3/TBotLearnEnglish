# webapp/routers/profile.py
from fastapi import APIRouter, Depends, HTTPException, status

import config.config as config
from database.cache import CachedUser, invalidate_user_cache
from database.engine import SessionLocal
from database.models import User
from filters.name import is_valid_name, normalize_name
from webapp.dependencies import get_current_user
from webapp.schemas import ProfileUpdateRequest

router = APIRouter(prefix="/api/me", tags=["profile"])


@router.get("")
async def api_me(user: CachedUser = Depends(get_current_user)):
    return {
        "user": user.to_dict(),
        "bot_username": config.BOT_USERNAME,
    }


@router.patch("/profile")
async def api_update_profile(
    payload: ProfileUpdateRequest,
    user: CachedUser = Depends(get_current_user),
):
    if not is_valid_name(payload.first_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректное имя: только буквы (допустим один дефис), 2–50 символов.",
        )
    if not is_valid_name(payload.last_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректная фамилия: только буквы (допустим один дефис), 2–50 символов.",
        )

    first = normalize_name(payload.first_name)
    last = normalize_name(payload.last_name)

    async with SessionLocal() as session:
        db_user = await session.get(User, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден.")
        db_user.first_name = first
        db_user.last_name = last
        await session.commit()

    await invalidate_user_cache(
        user.id,
        user.class_name,
        user.group_name,
        invalidate_teachers=(user.role in ("teacher", "admin", "founder")),
    )
    return {"ok": True, "first_name": first, "last_name": last}
