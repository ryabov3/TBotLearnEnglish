from webapp.schemas.admin import AdminUserUpdateRequest
from webapp.schemas.profile import ProfileUpdateRequest
from webapp.schemas.teacher import (
    AddStudentRequest,
    CreateGroupRequest,
    CreateTopicRequest,
    GradeSubmissionRequest,
    TaskItemInput,
)

__all__ = [
    "ProfileUpdateRequest",
    "CreateGroupRequest",
    "AddStudentRequest",
    "TaskItemInput",
    "CreateTopicRequest",
    "GradeSubmissionRequest",
    "AdminUserUpdateRequest",
]
