# database/models.py
from sqlalchemy import Integer, String, BigInteger, Text, ForeignKey, Boolean, Date
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from datetime import date

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)  # Имя
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)  # Фамилия
    role: Mapped[str] = mapped_column(String(50), default="student")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    class_name: Mapped[str] = mapped_column(String(50), nullable=True)
    group_name: Mapped[str] = mapped_column(String(50), nullable=True)

    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_task_date: Mapped[date] = mapped_column(Date, nullable=True)
    total_completed: Mapped[int] = mapped_column(Integer, default=0)
    max_tasks_per_day: Mapped[int] = mapped_column(Integer, default=0)
    tasks_today: Mapped[int] = mapped_column(Integer, default=0)


class StudyGroup(Base):
    __tablename__ = "study_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(BigInteger)
    class_name: Mapped[str] = mapped_column(String(50))
    group_name: Mapped[str] = mapped_column(String(50))


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    media_id: Mapped[str] = mapped_column(String(255), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), nullable=True)
    class_name: Mapped[str] = mapped_column(String(50))
    group_name: Mapped[str] = mapped_column(String(50))


class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"))
    student_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    media_id: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(50))
    grade: Mapped[int] = mapped_column(Integer, nullable=True)
    teacher_comment: Mapped[str] = mapped_column(Text, nullable=True)
