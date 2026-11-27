# handlers/admin.py
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from config.config import FOUNDERS_ID
from database.cache import (
    get_group_cached,
    get_group_students_cached,
    get_teacher_groups_cached,
    get_teachers_cached,
    get_user_cached,
    invalidate_user_cache,
)
from database.engine import SessionLocal
from database.models import Submission, Task, User
from filters import IsAdminFilter, IsFounderFilter
from keyboards.admin import (
    get_admin_back_kb,
    get_admin_paginated_list_kb,
    get_admin_panel_kb,
    get_cancel_admin_kb,
)
from lexicon import LEXICON
from states.states import AdminPanel

admin_router = Router()


async def _is_user_founder(user_id: int) -> bool:
    if user_id in FOUNDERS_ID:
        return True
    user = await get_user_cached(user_id)
    return bool(user and user.role == "founder")


async def show_admin_panel(
    message: types.Message, user_id: int, is_edit: bool = False
):
    is_founder = await _is_user_founder(user_id)
    text = LEXICON["panel_admin_title"]
    markup = get_admin_panel_kb(is_founder=is_founder)
    if is_edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=markup)


@admin_router.callback_query(F.data == "admin_back", IsAdminFilter())
async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await show_admin_panel(callback.message, callback.from_user.id, is_edit=True)


# ================= 👨‍🏫 ИЕРАРХИЯ: УЧИТЕЛЯ -> КЛАССЫ -> ГРУППЫ -> УЧЕНИКИ =================
@admin_router.callback_query(F.data.startswith("admtl_"), IsAdminFilter())
async def admin_list_teachers_pg(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[1])
    per_page = 5

    teachers = await get_teachers_cached()

    if not teachers:
        return await callback.message.edit_text(
            LEXICON["admin_no_teachers"],
            reply_markup=get_admin_back_kb("admin_back", "btn_back"),
        )

    total_pages = max(1, (len(teachers) + per_page - 1) // per_page)
    current_teachers = teachers[page * per_page : (page + 1) * per_page]

    buttons = []
    for t in current_teachers:
        name = f"{t.first_name or ''} {t.last_name or ''}".strip() or t.username or str(t.id)
        buttons.append((f"👨‍🏫 {name}", f"admt_{t.id}_0"))

    await callback.message.edit_text(
        LEXICON["admin_teachers_pg"].format(page=page + 1, total_pages=total_pages),
        parse_mode="HTML",
        reply_markup=get_admin_paginated_list_kb(
            buttons, page, total_pages, page_prefix="admtl_"
        ),
    )


@admin_router.callback_query(F.data.startswith("admt_"), IsAdminFilter())
async def admin_list_classes_pg(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    teacher_id = int(parts[1])
    page = int(parts[2])
    per_page = 6

    teacher = await get_user_cached(teacher_id)
    groups = await get_teacher_groups_cached(teacher_id)

    unique_classes = {}
    for g in groups:
        if g.class_name not in unique_classes:
            unique_classes[g.class_name] = g

    distinct_groups = list(unique_classes.values())

    if not distinct_groups:
        return await callback.message.edit_text(
            LEXICON["admin_teacher_no_classes"],
            reply_markup=get_admin_back_kb("admtl_0", "btn_adm_back_teachers"),
        )

    total_pages = max(1, (len(distinct_groups) + per_page - 1) // per_page)
    current_groups = distinct_groups[page * per_page : (page + 1) * per_page]

    buttons = [(f"🏫 Класс: {g.class_name}", f"admc_{g.id}_0") for g in current_groups]
    t_name = (
        f"{teacher.first_name or ''} {teacher.last_name or ''}".strip()
        or teacher.username
        or LEXICON["role_teacher_name"]
        if teacher
        else LEXICON["role_teacher_name"]
    )
    await callback.message.edit_text(
        LEXICON["admin_classes_pg"].format(
            teacher_name=t_name, page=page + 1, total_pages=total_pages
        ),
        parse_mode="HTML",
        reply_markup=get_admin_paginated_list_kb(
            buttons,
            page,
            total_pages,
            page_prefix=f"admt_{teacher_id}_",
            back_cb="admtl_0",
            back_text_key="btn_adm_back_teachers",
            columns=2,
        ),
    )


@admin_router.callback_query(F.data.startswith("admc_"), IsAdminFilter())
async def admin_list_groups_pg(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    base_group_id = int(parts[1])
    page = int(parts[2])
    per_page = 6

    base_group = await get_group_cached(base_group_id)
    if not base_group:
        return await callback.answer(LEXICON["admin_class_not_found"], show_alert=True)

    all_teacher_groups = await get_teacher_groups_cached(base_group.teacher_id)
    groups = [g for g in all_teacher_groups if g.class_name == base_group.class_name]

    if not groups:
        return await callback.message.edit_text(
            LEXICON["admin_class_no_groups"],
            reply_markup=get_admin_back_kb(
                f"admt_{base_group.teacher_id}_0", "btn_back"
            ),
        )

    total_pages = max(1, (len(groups) + per_page - 1) // per_page)
    current_groups = groups[page * per_page : (page + 1) * per_page]

    buttons = [(f"👥 {g.group_name}", f"admg_{g.id}_0") for g in current_groups]
    await callback.message.edit_text(
        LEXICON["admin_groups_pg"].format(
            class_name=base_group.class_name, page=page + 1, total_pages=total_pages
        ),
        parse_mode="HTML",
        reply_markup=get_admin_paginated_list_kb(
            buttons,
            page,
            total_pages,
            page_prefix=f"admc_{base_group_id}_",
            back_cb=f"admt_{base_group.teacher_id}_0",
            back_text_key="btn_adm_back_classes",
            columns=2,
        ),
    )


@admin_router.callback_query(F.data.startswith("admg_"), IsAdminFilter())
async def admin_list_students_pg(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    group_id = int(parts[1])
    page = int(parts[2])
    per_page = 5

    group = await get_group_cached(group_id)
    if not group:
        return await callback.answer(LEXICON["admin_group_not_found"], show_alert=True)

    students = await get_group_students_cached(group.class_name, group.group_name)

    if not students:
        return await callback.message.edit_text(
            LEXICON["admin_group_no_students"].format(group_name=group.group_name),
            parse_mode="HTML",
            reply_markup=get_admin_back_kb(f"admc_{group_id}_0", "btn_back"),
        )

    total_pages = max(1, (len(students) + per_page - 1) // per_page)
    current_students = students[page * per_page : (page + 1) * per_page]

    buttons = []
    for s in current_students:
        name = f"{s.first_name or ''} {s.last_name or ''}".strip() or s.username or str(s.id)
        buttons.append((f"👤 {name}", f"adms_{s.id}_{group_id}"))

    await callback.message.edit_text(
        LEXICON["admin_students_pg"].format(
            class_name=group.class_name,
            group_name=group.group_name,
            page=page + 1,
            total_pages=total_pages,
        ),
        parse_mode="HTML",
        reply_markup=get_admin_paginated_list_kb(
            buttons,
            page,
            total_pages,
            page_prefix=f"admg_{group_id}_",
            back_cb=f"admc_{group_id}_0",
            back_text_key="btn_adm_back_groups",
        ),
    )


@admin_router.callback_query(F.data.startswith("adms_"), IsAdminFilter())
async def admin_student_profile(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    student_id = int(parts[1])
    group_id = int(parts[2])

    user = await get_user_cached(student_id)
    if not user:
        return await callback.answer(LEXICON["admin_student_not_found"], show_alert=True)

    text = LEXICON["admin_student_dossier"].format(
        first_name=user.first_name or "Нет",
        last_name=user.last_name or "Нет",
        username=user.username or "Нет",
        status=LEXICON["admin_status_banned"]
        if user.is_banned
        else LEXICON["admin_status_active"],
        class_name=user.class_name or "Нет",
        group_name=user.group_name or "Нет",
        current_streak=user.current_streak,
        total_completed=user.total_completed,
        max_tasks_per_day=user.max_tasks_per_day,
    )

    async with SessionLocal() as session:
        subs = (
            await session.execute(
                select(Submission, Task)
                .join(Task, Submission.task_id == Task.id)
                .where(Submission.student_id == user.id)
                .order_by(Submission.id.desc())
                .limit(3)
            )
        ).all()

    if not subs:
        text += LEXICON["admin_no_answers"]
    for sub, task in subs:
        grade = (
            LEXICON["student_grade_label"].format(grade=sub.grade)
            if sub.grade
            else LEXICON["student_grade_not_checked"]
        )
        text += f"• {task.topic} | {task.title} ({grade})\n"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_back_kb(f"admg_{group_id}_0", "btn_adm_back_students"),
    )


# ================= ЛИЧНЫЕ СООБЩЕНИЯ =================
@admin_router.callback_query(F.data.startswith("admin_pml_"), IsAdminFilter())
async def admin_pm_list(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    per_page = 5

    async with SessionLocal() as session:
        users = (
            await session.execute(
                select(User)
                .where(User.id != callback.from_user.id)
                .order_by(User.role, User.id)
            )
        ).scalars().all()

    if not users:
        return await callback.message.edit_text(
            LEXICON["admin_no_other_users"], reply_markup=get_admin_back_kb()
        )

    total_pages = max(1, (len(users) + per_page - 1) // per_page)
    current_users = users[page * per_page : (page + 1) * per_page]

    buttons = []
    for u in current_users:
        emoji = (
            "👑"
            if u.role == "founder"
            else ("👨‍🏫" if u.role in ("teacher", "admin") else "👨‍🎓")
        )
        uname = f"(@{u.username})" if u.username else ""
        name = f"{u.first_name or ''} {u.last_name or ''}".strip() or str(u.id)
        buttons.append((f"{emoji} {uname} {name}".strip(), f"admin_pmu_{u.id}"))

    await callback.message.edit_text(
        LEXICON["admin_pm_list_pg"].format(page=page + 1, total_pages=total_pages),
        parse_mode="HTML",
        reply_markup=get_admin_paginated_list_kb(
            buttons, page, total_pages, page_prefix="admin_pml_"
        ),
    )


@admin_router.callback_query(F.data.startswith("admin_pmu_"), IsAdminFilter())
async def admin_pm_user(callback: types.CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split("_")[2])

    user = await get_user_cached(user_id)
    if not user:
        return await callback.answer(LEXICON["admin_user_not_found"], show_alert=True)

    await state.update_data(pm_target_id=user_id)
    await state.set_state(AdminPanel.waiting_for_personal_message)

    emoji = (
        "👑"
        if user.role == "founder"
        else ("👨‍🏫" if user.role in ("teacher", "admin") else "👨‍🎓")
    )
    uname = f"(@{user.username})" if user.username else ""
    name = f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user.id)
    user_label = f"{emoji} {uname} {name}".strip()

    await callback.message.edit_text(
        LEXICON["admin_pm_prompt"].format(user_label=user_label),
        parse_mode="HTML",
        reply_markup=get_cancel_admin_kb("admin_pml_0"),
    )


@admin_router.message(AdminPanel.waiting_for_personal_message, IsAdminFilter())
async def process_personal_message(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target_id = data.get("pm_target_id")

    full_message = LEXICON["admin_pm_received"].format(text=message.text)

    try:
        await message.bot.send_message(target_id, full_message, parse_mode="HTML")
        await message.answer(LEXICON["admin_pm_sent"])
    except Exception:
        await message.answer(LEXICON["admin_pm_failed"])

    await state.clear()
    await show_admin_panel(message, message.from_user.id, is_edit=False)


# ================= ДЕЙСТВИЯ ПОЛЬЗОВАТЕЛЯ =================
@admin_router.callback_query(F.data.startswith("adm_actl_"), IsAdminFilter())
async def admin_actions_list(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[-1])
    per_page = 5
    async with SessionLocal() as session:
        users = (await session.execute(select(User).order_by(User.id))).scalars().all()

    if not users:
        return await callback.message.edit_text(
            LEXICON["admin_no_users"], reply_markup=get_admin_back_kb()
        )

    total_pages = max(1, (len(users) + per_page - 1) // per_page)
    current_users = users[page * per_page : (page + 1) * per_page]

    buttons = []
    for u in current_users:
        emoji = (
            "👑"
            if u.role == "founder"
            else ("👨‍🏫" if u.role in ("teacher", "admin") else "👨‍🎓")
        )
        uname = f"(@{u.username})" if u.username else ""
        name = f"{u.first_name or ''} {u.last_name or ''}".strip() or str(u.id)
        buttons.append((f"{emoji} {uname} {name}".strip(), f"adm_actu_{u.id}"))

    await callback.message.edit_text(
        LEXICON["admin_actions_list_pg"].format(page=page + 1, total_pages=total_pages),
        parse_mode="HTML",
        reply_markup=get_admin_paginated_list_kb(
            buttons, page, total_pages, page_prefix="adm_actl_"
        ),
    )


@admin_router.callback_query(F.data.startswith("adm_actu_"), IsAdminFilter())
async def admin_actions_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])

    user = await get_user_cached(user_id)
    if not user:
        return await callback.answer(LEXICON["admin_user_not_found"], show_alert=True)

    text = LEXICON["admin_user_dossier_header"].format(
        first_name=user.first_name or "Нет",
        last_name=user.last_name or "Нет",
        username=user.username or "нет",
        role=user.role.upper(),
        status=LEXICON["admin_status_banned"]
        if user.is_banned
        else LEXICON["admin_status_active"],
    )

    if user.role == "student":
        text += LEXICON["admin_user_dossier_student"].format(
            class_name=user.class_name or "Нет",
            group_name=user.group_name or "Нет",
            current_streak=user.current_streak,
            total_completed=user.total_completed,
            max_tasks_per_day=user.max_tasks_per_day,
        )

        async with SessionLocal() as session:
            subs = (
                await session.execute(
                    select(Submission, Task)
                    .join(Task, Submission.task_id == Task.id)
                    .where(Submission.student_id == user.id)
                    .order_by(Submission.id.desc())
                    .limit(3)
                )
            ).all()

        if not subs:
            text += LEXICON["admin_no_answers"]
        for sub, task in subs:
            grade = (
                LEXICON["student_grade_label"].format(grade=sub.grade)
                if sub.grade
                else LEXICON["student_grade_not_checked"]
            )
            text += f"• {task.topic} | {task.title} ({grade})\n"

    elif user.role in ("teacher", "admin", "founder"):
        groups = await get_teacher_groups_cached(user.id)
        async with SessionLocal() as session:
            tasks = (
                await session.execute(select(Task).where(Task.teacher_id == user.id))
            ).scalars().all()

        text += LEXICON["admin_user_dossier_teacher"].format(
            groups_count=len(groups), tasks_count=len(tasks)
        )
        if not groups:
            text += LEXICON["admin_no_created_groups"]
        for g in groups:
            text += f"• {g.class_name} - {g.group_name}\n"

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_back_kb("adm_actl_0", "btn_adm_back_list"),
    )


# ================= ОТВЯЗАТЬ УЧЕНИКА ОТ ГРУППЫ =================
@admin_router.callback_query(F.data.startswith("adm_unl_"), IsAdminFilter())
async def admin_unlink_list(callback: types.CallbackQuery):
    try:
        page = int(callback.data.split("_")[-1])
    except ValueError:
        page = 0

    per_page = 5
    async with SessionLocal() as session:
        students = (
            await session.execute(
                select(User).where(User.role == "student", User.class_name != None)
            )
        ).scalars().all()

    if not students:
        return await callback.message.edit_text(
            LEXICON["admin_unlink_empty"], reply_markup=get_admin_back_kb()
        )

    total_pages = max(1, (len(students) + per_page - 1) // per_page)
    current_students = students[page * per_page : (page + 1) * per_page]

    buttons = [
        (
            f"👤 {s.first_name or ''} ({s.class_name}-{s.group_name})".strip(),
            f"adm_unlu_{s.id}",
        )
        for s in current_students
    ]

    await callback.message.edit_text(
        LEXICON["admin_unlink_pg"].format(page=page + 1, total_pages=total_pages),
        parse_mode="HTML",
        reply_markup=get_admin_paginated_list_kb(
            buttons, page, total_pages, page_prefix="adm_unl_"
        ),
    )


@admin_router.callback_query(F.data.startswith("adm_unlu_"), IsAdminFilter())
async def admin_unlink_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    old_class, old_group = None, None
    async with SessionLocal() as session:
        student = await session.get(User, user_id)
        if student:
            old_class, old_group = student.class_name, student.group_name
            student.class_name = None
            student.group_name = None
            await session.commit()

    await invalidate_user_cache(user_id, old_class, old_group)

    await callback.answer(LEXICON["admin_unlink_done"], show_alert=True)
    await admin_unlink_list(callback)


# ================= УПРАВЛЕНИЕ АДМИНАМИ (ТОЛЬКО FOUNDER) =================
@admin_router.callback_query(
    F.data.in_(["admin_add_admin", "admin_rem_admin"]), IsFounderFilter()
)
async def founder_admin_callbacks(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "admin_add_admin":
        await callback.message.edit_text(
            LEXICON["admin_prompt_add_admin"], reply_markup=get_cancel_admin_kb()
        )
        await state.set_state(AdminPanel.waiting_for_username_add_admin)
    else:
        await callback.message.edit_text(
            LEXICON["admin_prompt_rem_admin"], reply_markup=get_cancel_admin_kb()
        )
        await state.set_state(AdminPanel.waiting_for_username_rem_admin)
    await callback.answer()


# ================= УПРАВЛЕНИЕ РОЛЯМИ И РАССЫЛКИ =================
@admin_router.callback_query(F.data.startswith("admin_"), IsAdminFilter())
async def admin_callbacks(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data
    if action == "admin_add_teacher":
        await callback.message.edit_text(
            LEXICON["admin_prompt_add_teacher"], reply_markup=get_cancel_admin_kb()
        )
        await state.set_state(AdminPanel.waiting_for_username_teacher)
    elif action == "admin_rem_teacher":
        await callback.message.edit_text(
            LEXICON["admin_prompt_rem_teacher"], reply_markup=get_cancel_admin_kb()
        )
        await state.set_state(AdminPanel.waiting_for_username_remove)
    elif action == "admin_ban":
        await callback.message.edit_text(
            LEXICON["admin_prompt_ban"], reply_markup=get_cancel_admin_kb()
        )
        await state.set_state(AdminPanel.waiting_for_username_ban)
    elif action == "admin_unban":
        await callback.message.edit_text(
            LEXICON["admin_prompt_unban"], reply_markup=get_cancel_admin_kb()
        )
        await state.set_state(AdminPanel.waiting_for_username_unban)
    elif action == "admin_broad_student":
        await state.update_data(broadcast_target="student")
        await callback.message.edit_text(
            LEXICON["admin_prompt_broad_student"],
            parse_mode="HTML",
            reply_markup=get_cancel_admin_kb(),
        )
        await state.set_state(AdminPanel.waiting_for_broadcast_text)
    elif action == "admin_broad_teacher":
        await state.update_data(broadcast_target="teacher")
        await callback.message.edit_text(
            LEXICON["admin_prompt_broad_teacher"],
            parse_mode="HTML",
            reply_markup=get_cancel_admin_kb(),
        )
        await state.set_state(AdminPanel.waiting_for_broadcast_text)
    await callback.answer()


@admin_router.message(AdminPanel.waiting_for_broadcast_text, IsAdminFilter())
async def process_broadcast(message: types.Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("broadcast_target")

    async with SessionLocal() as session:
        users = (
            await session.execute(
                select(User).where(User.role == target, User.is_banned == False)
            )
        ).scalars().all()

    count = 0
    full_message = LEXICON["admin_broadcast_received"].format(text=message.text)

    for u in users:
        try:
            await message.bot.send_message(u.id, full_message, parse_mode="HTML")
            count += 1
        except Exception:
            pass

    await message.answer(
        LEXICON["admin_broadcast_done"].format(count=count, target=target)
    )
    await state.clear()
    await show_admin_panel(message, message.from_user.id, is_edit=False)


async def update_user_by_username(
    message: types.Message, state: FSMContext, field: str, value
):
    username = message.text.replace("@", "").strip()
    updated_user_info = None
    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                LEXICON["admin_update_user_not_found"].format(username=username)
            )
        elif user.role == "founder":
            await message.answer(LEXICON["admin_cannot_modify_founder"])
        else:
            setattr(user, field, value)
            await session.commit()
            updated_user_info = (user.id, user.class_name, user.group_name)
            await message.answer(
                LEXICON["admin_update_user_done"].format(username=username)
            )

    if updated_user_info is not None:
        uid, c_name, g_name = updated_user_info
        await invalidate_user_cache(
            uid,
            c_name,
            g_name,
            invalidate_teachers=(field == "role"),
        )

    await state.clear()
    await show_admin_panel(message, message.from_user.id, is_edit=False)


@admin_router.message(AdminPanel.waiting_for_username_teacher, IsAdminFilter())
async def set_teacher(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "role", "teacher")


@admin_router.message(AdminPanel.waiting_for_username_remove, IsAdminFilter())
async def rem_teacher(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "role", "student")


@admin_router.message(AdminPanel.waiting_for_username_add_admin, IsFounderFilter())
async def set_admin(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "role", "admin")


@admin_router.message(AdminPanel.waiting_for_username_rem_admin, IsFounderFilter())
async def rem_admin(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "role", "student")


@admin_router.message(AdminPanel.waiting_for_username_ban, IsAdminFilter())
async def ban_user(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "is_banned", True)


@admin_router.message(AdminPanel.waiting_for_username_unban, IsAdminFilter())
async def unban_user(message: types.Message, state: FSMContext):
    await update_user_by_username(message, state, "is_banned", False)
