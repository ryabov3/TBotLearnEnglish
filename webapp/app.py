# webapp/app.py
"""FastAPI бэкенд для Telegram Mini App (TBotLearnEnglish)."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select

import config.config as config
from database.cache import (
    CachedUser,
    get_group_cached,
    get_group_students_cached,
    get_group_tasks_cached,
    get_task_cached,
    get_teacher_groups_cached,
    invalidate_group_stats_cache,
    invalidate_group_students_cache,
    invalidate_group_tasks_cache,
    invalidate_tasks_cache,
    invalidate_teacher_groups_cache,
    invalidate_user_cache,
)
from database.engine import SessionLocal
from database.models import StudyGroup, Submission, Task, User
from filters.name import is_valid_name, normalize_name
from webapp.auth import get_current_user, require_roles

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="TBotLearnEnglish Mini App", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ================= СХЕМЫ ЗАПРОСОВ =================
class ProfileUpdateRequest(BaseModel):
    first_name: str
    last_name: str


class CreateGroupRequest(BaseModel):
    class_name: str = Field(..., min_length=1, max_length=50)
    group_name: str = Field(..., min_length=1, max_length=50)


class AddStudentRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)


class TaskItemInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1, max_length=3000)
    expected_answer: Literal["audio", "video", "any"] = "any"


class CreateTopicRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=250)
    group_ids: list[int] = Field(..., min_length=1)
    tasks: list[TaskItemInput] = Field(..., min_length=1)


class GradeSubmissionRequest(BaseModel):
    grade: int = Field(..., ge=1, le=5)
    comment: str = Field(default="", max_length=1500)


class AdminUserUpdateRequest(BaseModel):
    role: Literal["student", "teacher", "admin"] | None = None
    is_banned: bool | None = None
    unlink_group: bool = False


# ================= СТАТИКА И HEALTH =================
@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# ================= ПРОФИЛЬ (ВСЕ РОЛИ) =================
@app.get("/api/me")
async def api_me(user: CachedUser = Depends(get_current_user)):
    return {
        "user": user.to_dict(),
        "bot_username": config.BOT_USERNAME,
    }


@app.patch("/api/me/profile")
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


# ================= УЧЕНИК =================
@app.get("/api/student/topics")
async def api_student_topics(user: CachedUser = Depends(get_current_user)):
    if not user.class_name or not user.group_name:
        return {"has_group": False, "new_topics": [], "in_progress": [], "completed_topics": []}

    all_tasks = await get_group_tasks_cached(user.class_name, user.group_name)
    async with SessionLocal() as session:
        subs_res = await session.execute(
            select(Submission.task_id).where(Submission.student_id == user.id)
        )
        completed_ids = {r[0] for r in subs_res.all()}

    topics_map: dict[str, dict] = {}
    for t in all_tasks:
        entry = topics_map.setdefault(
            t.topic,
            {
                "topic": t.topic,
                "total": 0,
                "completed": 0,
                "first_uncompleted_id": None,
                "tasks": [],
            },
        )
        is_done = t.id in completed_ids
        entry["total"] += 1
        if is_done:
            entry["completed"] += 1
        elif entry["first_uncompleted_id"] is None:
            entry["first_uncompleted_id"] = t.id
        entry["tasks"].append(
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "expected_answer": t.expected_answer,
                "has_media": bool(t.media_id),
                "completed": is_done,
            }
        )

    new_topics, in_progress, completed_topics = [], [], []
    for item in topics_map.values():
        if item["completed"] == 0:
            new_topics.append(item)
        elif item["completed"] < item["total"]:
            in_progress.append(item)
        else:
            completed_topics.append(item)

    return {
        "has_group": True,
        "class_name": user.class_name,
        "group_name": user.group_name,
        "new_topics": new_topics,
        "in_progress": in_progress,
        "completed_topics": completed_topics,
    }


@app.get("/api/student/submissions")
async def api_student_submissions(user: CachedUser = Depends(get_current_user)):
    async with SessionLocal() as session:
        res = await session.execute(
            select(Submission, Task)
            .join(Task, Submission.task_id == Task.id)
            .where(Submission.student_id == user.id)
            .order_by(Submission.id.desc())
            .limit(30)
        )
        rows = res.all()

    return {
        "submissions": [
            {
                "id": sub.id,
                "task_id": task.id,
                "topic": task.topic,
                "title": task.title,
                "description": task.description,
                "grade": sub.grade,
                "teacher_comment": sub.teacher_comment,
                "media_type": sub.media_type,
            }
            for sub, task in rows
        ]
    }


# ================= УЧИТЕЛЬ =================
@app.get("/api/teacher/groups")
async def api_teacher_groups(user: CachedUser = Depends(get_current_user)):
    require_roles(user, ("teacher", "admin", "founder"))
    groups = await get_teacher_groups_cached(user.id)
    result = []
    for g in groups:
        students = await get_group_students_cached(g.class_name, g.group_name)
        tasks = await get_group_tasks_cached(
            g.class_name, g.group_name, teacher_id=user.id
        )
        result.append(
            {
                "id": g.id,
                "class_name": g.class_name,
                "group_name": g.group_name,
                "students_count": len(students),
                "tasks_count": len(tasks),
            }
        )
    return {"groups": result}


@app.post("/api/teacher/groups")
async def api_teacher_create_group(
    payload: CreateGroupRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("teacher", "admin", "founder"))
    c_name = payload.class_name.strip()
    g_name = payload.group_name.strip()

    async with SessionLocal() as session:
        new_group = StudyGroup(
            teacher_id=user.id, class_name=c_name, group_name=g_name
        )
        session.add(new_group)
        await session.commit()
        await session.refresh(new_group)
        gid = new_group.id

    await invalidate_teacher_groups_cache(user.id)
    return {"ok": True, "id": gid, "class_name": c_name, "group_name": g_name}


@app.get("/api/teacher/groups/{group_id}/students")
async def api_teacher_group_students(
    group_id: int, user: CachedUser = Depends(get_current_user)
):
    require_roles(user, ("teacher", "admin", "founder"))
    group = await get_group_cached(group_id)
    if not group or (group.teacher_id != user.id and user.role == "teacher"):
        raise HTTPException(status_code=404, detail="Группа не найдена.")

    students = await get_group_students_cached(group.class_name, group.group_name)
    return {
        "group": group.to_dict(),
        "students": [s.to_dict() for s in students],
    }


@app.post("/api/teacher/groups/{group_id}/students")
async def api_teacher_add_student(
    group_id: int,
    payload: AddStudentRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("teacher", "admin", "founder"))
    group = await get_group_cached(group_id)
    if not group or (group.teacher_id != user.id and user.role == "teacher"):
        raise HTTPException(status_code=404, detail="Группа не найдена.")

    username = payload.username.replace("@", "").strip()
    old_class = old_group = None
    async with SessionLocal() as session:
        res = await session.execute(select(User).where(User.username == username))
        student = res.scalar_one_or_none()
        if not student:
            raise HTTPException(
                status_code=404,
                detail=f"Ученик @{username} не найден. Он должен запустить бота (/start).",
            )
        old_class, old_group = student.class_name, student.group_name
        student.class_name = group.class_name
        student.group_name = group.group_name
        await session.commit()
        student_id = student.id

    await invalidate_user_cache(student_id, group.class_name, group.group_name)
    if old_class and old_group and (
        old_class != group.class_name or old_group != group.group_name
    ):
        await invalidate_group_students_cache(old_class, old_group)

    return {"ok": True, "student_id": student_id}


@app.delete("/api/teacher/groups/{group_id}/students/{student_id}")
async def api_teacher_remove_student(
    group_id: int,
    student_id: int,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("teacher", "admin", "founder"))
    group = await get_group_cached(group_id)
    if not group or (group.teacher_id != user.id and user.role == "teacher"):
        raise HTTPException(status_code=404, detail="Группа не найдена.")

    old_class = old_group = None
    async with SessionLocal() as session:
        student = await session.get(User, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Ученик не найден.")
        old_class, old_group = student.class_name, student.group_name
        student.class_name = None
        student.group_name = None
        await session.commit()

    await invalidate_user_cache(student_id, old_class, old_group)
    return {"ok": True}


@app.get("/api/teacher/topics")
async def api_teacher_topics(user: CachedUser = Depends(get_current_user)):
    require_roles(user, ("teacher", "admin", "founder"))
    async with SessionLocal() as session:
        tasks = (
            await session.execute(
                select(Task).where(Task.teacher_id == user.id).order_by(Task.id.desc())
            )
        ).scalars().all()

    grouped: dict[str, dict] = {}
    for t in tasks:
        item = grouped.setdefault(
            t.topic, {"topic": t.topic, "groups": set(), "tasks_count": 0}
        )
        item["groups"].add(f"{t.class_name} - {t.group_name}")
        item["tasks_count"] += 1

    return {
        "topics": [
            {
                "topic": v["topic"],
                "groups": sorted(v["groups"]),
                "tasks_count": v["tasks_count"],
            }
            for v in grouped.values()
        ]
    }


@app.post("/api/teacher/topics")
async def api_teacher_create_topic(
    payload: CreateTopicRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("teacher", "admin", "founder"))
    affected_groups: set[tuple[str, str]] = set()
    created_count = 0

    async with SessionLocal() as session:
        for gid in payload.group_ids:
            group = await session.get(StudyGroup, gid)
            if not group or (group.teacher_id != user.id and user.role == "teacher"):
                continue
            affected_groups.add((group.class_name, group.group_name))
            for item in payload.tasks:
                session.add(
                    Task(
                        teacher_id=user.id,
                        topic=payload.topic.strip(),
                        title=item.title.strip(),
                        description=item.description.strip(),
                        class_name=group.class_name,
                        group_name=group.group_name,
                        expected_answer=item.expected_answer,
                    )
                )
                created_count += 1
        if created_count == 0:
            raise HTTPException(
                status_code=400, detail="Не выбрано ни одной валидной группы."
            )
        await session.commit()

    for c_name, g_name in affected_groups:
        await invalidate_group_tasks_cache(c_name, g_name)
        await invalidate_group_stats_cache(user.id, c_name, g_name)

    return {"ok": True, "created_tasks": created_count}


@app.delete("/api/teacher/topics/{topic_name:path}")
async def api_teacher_delete_topic(
    topic_name: str,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("teacher", "admin", "founder"))
    async with SessionLocal() as session:
        res = await session.execute(
            select(Task.id, Task.class_name, Task.group_name).where(
                Task.teacher_id == user.id, Task.topic == topic_name
            )
        )
        rows = res.all()
        if not rows:
            raise HTTPException(status_code=404, detail="Тема не найдена.")

        task_ids = [r[0] for r in rows]
        affected_groups = {(r[1], r[2]) for r in rows}
        await session.execute(
            delete(Submission).where(Submission.task_id.in_(task_ids))
        )
        await session.execute(delete(Task).where(Task.id.in_(task_ids)))
        await session.commit()

    await invalidate_tasks_cache(task_ids)
    for c_name, g_name in affected_groups:
        await invalidate_group_tasks_cache(c_name, g_name)
        await invalidate_group_stats_cache(user.id, c_name, g_name)

    return {"ok": True, "deleted_tasks": len(task_ids)}


@app.get("/api/teacher/submissions")
async def api_teacher_submissions(
    status_filter: Literal["pending", "graded"] = "pending",
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("teacher", "admin", "founder"))
    async with SessionLocal() as session:
        stmt = (
            select(Submission, Task, User)
            .join(Task, Submission.task_id == Task.id)
            .join(User, Submission.student_id == User.id)
            .where(Task.teacher_id == user.id)
        )
        if status_filter == "pending":
            stmt = stmt.where(Submission.grade == None)
        else:
            stmt = stmt.where(Submission.grade != None)
        stmt = stmt.order_by(Submission.id.desc()).limit(50)
        rows = (await session.execute(stmt)).all()

    return {
        "submissions": [
            {
                "id": sub.id,
                "task_id": task.id,
                "topic": task.topic,
                "title": task.title,
                "class_name": task.class_name,
                "group_name": task.group_name,
                "student_name": f"{student.first_name or ''} {student.last_name or ''}".strip()
                or student.username
                or str(student.id),
                "student_username": student.username,
                "media_type": sub.media_type,
                "grade": sub.grade,
                "teacher_comment": sub.teacher_comment,
            }
            for sub, task, student in rows
        ]
    }


@app.post("/api/teacher/submissions/{sub_id}/grade")
async def api_teacher_grade_submission(
    sub_id: int,
    payload: GradeSubmissionRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("teacher", "admin", "founder"))
    async with SessionLocal() as session:
        sub = await session.get(Submission, sub_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Ответ не найден.")
        task = await session.get(Task, sub.task_id)
        if not task or (task.teacher_id != user.id and user.role == "teacher"):
            raise HTTPException(status_code=403, detail="Нет доступа к этому заданию.")
        sub.grade = payload.grade
        sub.teacher_comment = payload.comment.strip() or None
        await session.commit()
        t_teacher_id, t_class, t_group = task.teacher_id, task.class_name, task.group_name

    await invalidate_group_stats_cache(t_teacher_id, t_class, t_group)
    return {"ok": True}


@app.get("/api/teacher/groups/{group_id}/stats")
async def api_teacher_group_stats(
    group_id: int, user: CachedUser = Depends(get_current_user)
):
    require_roles(user, ("teacher", "admin", "founder"))
    group = await get_group_cached(group_id)
    if not group or (group.teacher_id != user.id and user.role == "teacher"):
        raise HTTPException(status_code=404, detail="Группа не найдена.")

    tasks = await get_group_tasks_cached(
        group.class_name, group.group_name, teacher_id=user.id
    )
    students = await get_group_students_cached(group.class_name, group.group_name)

    grades_by_task: dict[int, list[int]] = defaultdict(list)
    subs_by_student: dict[int, list[int]] = defaultdict(list)

    if tasks:
        task_ids = [t.id for t in tasks]
        async with SessionLocal() as session:
            sub_res = await session.execute(
                select(Submission.task_id, Submission.student_id, Submission.grade).where(
                    Submission.task_id.in_(task_ids)
                )
            )
            for tid, sid, grade in sub_res.all():
                if grade is not None:
                    grades_by_task[tid].append(grade)
                    subs_by_student[sid].append(grade)

    task_stats = []
    all_grades: list[int] = []
    for t in tasks:
        g_list = grades_by_task.get(t.id, [])
        all_grades.extend(g_list)
        task_stats.append(
            {
                "id": t.id,
                "topic": t.topic,
                "title": t.title,
                "avg": round(sum(g_list) / len(g_list), 2) if g_list else None,
                "graded_count": len(g_list),
            }
        )

    student_stats = []
    for s in students:
        sg = subs_by_student.get(s.id, [])
        student_stats.append(
            {
                "id": s.id,
                "name": f"{s.first_name or ''} {s.last_name or ''}".strip()
                or s.username
                or str(s.id),
                "avg": round(sum(sg) / len(sg), 2) if sg else None,
                "graded_count": len(sg),
                "total_completed": s.total_completed,
                "current_streak": s.current_streak,
            }
        )

    return {
        "group": group.to_dict(),
        "overall_avg": round(sum(all_grades) / len(all_grades), 2) if all_grades else None,
        "tasks": task_stats,
        "students": student_stats,
    }


# ================= АДМИН И ОСНОВАТЕЛЬ =================
@app.get("/api/admin/overview")
async def api_admin_overview(user: CachedUser = Depends(get_current_user)):
    require_roles(user, ("admin", "founder"))
    async with SessionLocal() as session:
        users = (await session.execute(select(User).order_by(User.id))).scalars().all()
        groups_count = (await session.execute(select(func.count(StudyGroup.id)))).scalar() or 0
        tasks_count = (await session.execute(select(func.count(Task.id)))).scalar() or 0
        subs_count = (await session.execute(select(func.count(Submission.id)))).scalar() or 0

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


@app.patch("/api/admin/users/{target_id}")
async def api_admin_update_user(
    target_id: int,
    payload: AdminUserUpdateRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, ("admin", "founder"))
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
