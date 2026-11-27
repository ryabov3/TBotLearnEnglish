# webapp/routers/teacher.py
from collections import defaultdict
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select

from database.cache import (
    CachedUser,
    get_group_cached,
    get_group_students_cached,
    get_group_tasks_cached,
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
from webapp.dependencies import get_current_user, require_roles
from webapp.schemas import (
    AddStudentRequest,
    CreateGroupRequest,
    CreateTopicRequest,
    GradeSubmissionRequest,
)

router = APIRouter(prefix="/api/teacher", tags=["teacher"])
TEACHER_ROLES = ("teacher", "admin", "founder")


@router.get("/groups")
async def api_teacher_groups(user: CachedUser = Depends(get_current_user)):
    require_roles(user, TEACHER_ROLES)
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


@router.post("/groups")
async def api_teacher_create_group(
    payload: CreateGroupRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, TEACHER_ROLES)
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


@router.get("/groups/{group_id}/students")
async def api_teacher_group_students(
    group_id: int, user: CachedUser = Depends(get_current_user)
):
    require_roles(user, TEACHER_ROLES)
    group = await get_group_cached(group_id)
    if not group or (group.teacher_id != user.id and user.role == "teacher"):
        raise HTTPException(status_code=404, detail="Группа не найдена.")

    students = await get_group_students_cached(group.class_name, group.group_name)
    return {
        "group": group.to_dict(),
        "students": [s.to_dict() for s in students],
    }


@router.post("/groups/{group_id}/students")
async def api_teacher_add_student(
    group_id: int,
    payload: AddStudentRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, TEACHER_ROLES)
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


@router.delete("/groups/{group_id}/students/{student_id}")
async def api_teacher_remove_student(
    group_id: int,
    student_id: int,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, TEACHER_ROLES)
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


@router.get("/topics")
async def api_teacher_topics(user: CachedUser = Depends(get_current_user)):
    require_roles(user, TEACHER_ROLES)
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


@router.post("/topics")
async def api_teacher_create_topic(
    payload: CreateTopicRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, TEACHER_ROLES)
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


@router.delete("/topics/{topic_name:path}")
async def api_teacher_delete_topic(
    topic_name: str,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, TEACHER_ROLES)
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


@router.get("/submissions")
async def api_teacher_submissions(
    status_filter: Literal["pending", "graded"] = "pending",
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, TEACHER_ROLES)
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


@router.post("/submissions/{sub_id}/grade")
async def api_teacher_grade_submission(
    sub_id: int,
    payload: GradeSubmissionRequest,
    user: CachedUser = Depends(get_current_user),
):
    require_roles(user, TEACHER_ROLES)
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


@router.get("/groups/{group_id}/stats")
async def api_teacher_group_stats(
    group_id: int, user: CachedUser = Depends(get_current_user)
):
    require_roles(user, TEACHER_ROLES)
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
