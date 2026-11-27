# webapp/schemas/teacher.py
from typing import Literal

from pydantic import BaseModel, Field


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
