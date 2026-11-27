from webapp.routers.admin import router as admin_router
from webapp.routers.health import router as health_router
from webapp.routers.profile import router as profile_router
from webapp.routers.student import router as student_router
from webapp.routers.teacher import router as teacher_router

__all__ = [
    "health_router",
    "profile_router",
    "student_router",
    "teacher_router",
    "admin_router",
]
