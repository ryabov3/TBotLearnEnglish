# webapp/main.py
"""Точка входа FastAPI API для Telegram Mini App."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.cache import close_redis
from webapp.middlewares import RequestLoggingMiddleware
from webapp.routers import (
    admin_router,
    health_router,
    profile_router,
    student_router,
    teacher_router,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await close_redis()


def create_app() -> FastAPI:
    application = FastAPI(
        title="TBotLearnEnglish Mini App API",
        version="2.0.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(RequestLoggingMiddleware)

    application.include_router(health_router)
    application.include_router(profile_router)
    application.include_router(student_router)
    application.include_router(teacher_router)
    application.include_router(admin_router)

    return application


app = create_app()
