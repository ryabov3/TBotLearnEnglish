# webapp/routers/student.py
from fastapi import APIRouter, Depends
from sqlalchemy import select

from database.cache import CachedUser, get_group_tasks_cached
from database.engine import SessionLocal
from database.models import Submission, Task
from webapp.dependencies import get_current_user

router = APIRouter(prefix="/api/student", tags=["student"])


@router.get("/topics")
async def api_student_topics(user: CachedUser = Depends(get_current_user)):
    if not user.class_name or not user.group_name:
        return {
            "has_group": False,
            "new_topics": [],
            "in_progress": [],
            "completed_topics": [],
        }

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


@router.get("/submissions")
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
