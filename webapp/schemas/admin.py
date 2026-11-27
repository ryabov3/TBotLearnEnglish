# webapp/schemas/admin.py
from typing import Literal

from pydantic import BaseModel


class AdminUserUpdateRequest(BaseModel):
    role: Literal["student", "teacher", "admin"] | None = None
    is_banned: bool | None = None
    unlink_group: bool = False
