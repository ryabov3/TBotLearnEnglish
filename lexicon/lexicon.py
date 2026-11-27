# lexicon/lexicon.py
"""Словарь всех текстовых фраз, команд, кнопок и описаний бота."""

LEXICON: dict[str, str] = {
    # ================= КОМАНДЫ БОТА =================
    "cmd_start_desc": "Начать работу / Главное меню",

    # ================= ОБЩИЕ И ДОСТУП =================
    "not_registered": (
        "⚠️ Вы ещё не зарегистрированы в боте.\n\n"
        "Пожалуйста, пройдите регистрацию через команду /start."
    ),
    "not_registered_alert": "Вы не зарегистрированы! Пройдите регистрацию через /start.",
    "user_banned": "❌ Вы заблокированы администратором.",
    "no_admin_rights": "❌ У вас нет прав администратора.",
    "no_teacher_rights": "❌ Этот раздел доступен только учителям.",
    "role_student_name": "Ученик",
    "role_teacher_name": "Учитель",
    "role_admin_name": "Администратор",
    "role_founder_name": "Основатель",
    "no_username": "Без_юзернейма",
    "no_group": "Нет группы",
    "no_class": "Нет класса",
    "no_comment": "Нет комментария",

    # ================= РЕГИСТРАЦИЯ =================
    "reg_welcome_choose_role": (
        "👋 <b>Привет!</b> Добро пожаловать в бота для тренировки английского произношения.\n\n"
        "Для начала выберите вашу <b>роль</b>:"
    ),
    "reg_welcome_admin": (
        "👋 Привет! Для начала работы нам нужно познакомиться.\n\n"
        "Введите ваше <b>Имя</b>:"
    ),
    "reg_role_selected": (
        "Вы выбрали роль: <b>{role_label}</b>.\n\n"
        "Теперь введите ваше <b>Имя</b>:"
    ),
    "reg_enter_first_name": "Пожалуйста, сначала введите свое <b>Имя</b>:",
    "reg_enter_last_name": "Отлично! Теперь введите вашу <b>Фамилию</b>:",
    "reg_confirm_data": (
        "Ваши данные:\n"
        "Роль: <b>{role_label}</b>\n"
        "Имя: <b>{first_name}</b>\n"
        "Фамилия: <b>{last_name}</b>\n\n"
        "Всё верно?"
    ),
    "reg_saved": "✅ Отлично! Регистрация завершена, данные сохранены.",
    "reg_retry_choose_role": "Давай попробуем снова. Выберите вашу <b>роль</b>:",
    "reg_retry_first_name": "Давай попробуем снова. Введите ваше <b>Имя</b>:",

    # ================= ГЛАВНЫЕ ПАНЕЛИ =================
    "panel_teacher_title": "👨‍🏫 <b>Панель Учителя</b>\nВыберите действие:",
    "panel_student_title": "🎓 <b>Панель Ученика</b>\nЧто хочешь сделать?",
    "panel_admin_title": "<b>🛠 Панель администратора</b>\nВыберите действие:",

    # ================= ПРОФИЛЬ УЧЕНИКА =================
    "student_profile": (
        "👤 <b>Профиль:</b> {first_name} {last_name} (@{username})\n"
        "🎓 <b>Роль:</b> {role_label}\n"
        "🏫 <b>Класс/Группа:</b> {class_name} / {group_name}\n\n"
        "📊 <b>Твоя статистика:</b>\n"
        "🔥 <b>Дней подряд:</b> {current_streak}\n"
        "✅ <b>Всего заданий:</b> {total_completed}\n"
        "🏆 <b>Максимум в день:</b> {max_tasks_per_day}\n"
    ),
    "edit_first_name_prompt": "Введите свое новое <b>Имя</b>:",
    "edit_last_name_prompt": "Теперь введите новую <b>Фамилию</b>:",
    "edit_name_success": "✅ Имя и фамилия успешно изменены!",

    # ================= ЗАДАНИЯ УЧЕНИКА =================
    "student_no_completed": "У тебя пока нет выполненных заданий.",
    "student_completed_title": "✅ <b>Последние выполненные задания:</b>",
    "student_grade_label": "Оценка: {grade}",
    "student_grade_pending": "⏳ На проверке",
    "student_grade_not_checked": "⏳ Ещё не проверено",
    "student_submission_details": (
        "Тема: <b>{topic}</b>\n"
        "📝 <b>Задание:</b> {title}\n"
        "📖 <b>Описание:</b> {description}\n\n"
        "⭐️ <b>Твоя оценка:</b> {grade}\n"
        "👨‍🏫 <b>Комментарий учителя:</b> {comment}"
    ),
    "student_no_group": "Учитель еще не добавил тебя в группу!",
    "student_topics_progress_title": "⏳ <b>Темы в процессе:</b>",
    "student_topics_new_title": "🆕 <b>Новые темы:</b>",
    "student_topics_progress_empty": "У тебя нет тем в процессе выполнения.",
    "student_topics_new_empty": "🎉 Ура! У тебя нет новых тем на сегодня.",
    "task_not_found": "Задание не найдено.",
    "task_not_found_or_deleted": "❌ Задание не найдено или было удалено.",
    "student_task_card": (
        "📂 Тема: <b>{topic}</b>\n\n"
        "📝 <b>Задание:</b> {title}\n\n"
        "{description}"
    ),
    "teacher_attachment": "👇 Вложение от учителя:",
    "req_format_any": "🤷‍♂️ Любой формат (Аудио или Видео)",
    "req_format_audio": "🎤 Только Аудио/Голосовое",
    "req_format_video": "📹 Только Видео/Кружок",
    "student_task_instructions": (
        "⚠️ <b>Формат ответа:</b> {req_text}\n\n"
        "Запиши и отправь свой ответ 🎤\n"
        "<i>(Ты сможешь прослушать/посмотреть его перед отправкой учителю)</i>"
    ),
    "student_answer_invalid_media": (
        "❌ Ответ на задание должен быть записан как медиа-файл "
        "(голосовое, аудио, видео-кружок или видео). Попробуйте еще раз!"
    ),
    "student_answer_only_audio": (
        "❌ <b>Ошибка формата!</b>\n"
        "Ответ на это задание может быть <b>только аудио</b> "
        "(учитель выбрал: Аудио/Голосовое).\n\nЗапишите голосовое сообщение."
    ),
    "student_answer_only_video": (
        "❌ <b>Ошибка формата!</b>\n"
        "Ответ на это задание может быть <b>только видео</b> "
        "(учитель выбрал: Видео/Кружок).\n\nЗапишите видео-сообщение."
    ),
    "student_answer_confirm": (
        "Я получил твой ответ! Хочешь отправить его учителю или записать заново?"
    ),
    "student_answer_retry": "Хорошо, жду новый вариант. Запиши и отправь правильный формат 🎤",
    "student_answer_sent_more": "✅ Ответ отправлен! В этой теме есть еще задания. Продолжим?",
    "student_topic_finished": (
        "🎉 <b>Поздравляю!</b> Ты полностью завершил тему <b>«{topic}»</b>! "
        "Ответы отправлены учителю."
    ),

    # ================= УЧИТЕЛЬ: КЛАССЫ И УЧЕНИКИ =================
    "teacher_no_classes": "У вас пока нет созданных классов.",
    "teacher_no_groups": "У вас пока нет созданных групп.",
    "teacher_no_groups_create": "❌ У вас еще нет групп. Сначала создайте группу.",
    "teacher_no_groups_short": "❌ У вас еще нет групп.",
    "teacher_no_groups_panel": "❌ Сначала создайте классы в панели управления.",
    "teacher_choose_class_pg": "Выберите класс (Страница {page} из {total_pages}):",
    "group_not_found": "Группа не найдена.",
    "teacher_class_empty": "В классе <b>{class_name} - {group_name}</b> пока нет учеников.",
    "teacher_class_list_header": "📋 <b>Список: {class_name} - {group_name}</b>\n\n",
    "teacher_enter_class_name": "Введи название класса (например, 5А):",
    "teacher_enter_group_name": "Введи название группы (например, Группа 1):",
    "teacher_group_saved": "✅ Класс и группа успешно сохранены!",
    "teacher_choose_group_add_student": "Выберите класс и группу, куда добавить ученика:",
    "teacher_group_selected_username": (
        "Группа выбрана ({class_name} - {group_name}).\n"
        "Теперь отправьте @юзернейм ученика:"
    ),
    "teacher_student_not_found": "❌ Ученик @{username} не найден. Он должен запустить бота.",
    "teacher_student_added": "✅ Ученик @{username} успешно добавлен в {class_name} - {group_name}!",
    "teacher_choose_group_rem_student": "Выберите группу для удаления ученика:",
    "teacher_group_no_students": "В этой группе пока нет учеников.",
    "teacher_rem_student_pg": (
        "Группа: <b>{class_name} - {group_name}</b>\n"
        "Выберите ученика для удаления (Стр. {page}/{total_pages}):"
    ),
    "teacher_student_removed_alert": "Ученик удален из группы!",

    # ================= УЧИТЕЛЬ: СОЗДАНИЕ И УДАЛЕНИЕ ЗАДАНИЙ =================
    "teacher_enter_topic": "Введи название <b>общей темы</b> (например, 'Хобби'):",
    "teacher_topic_too_long": (
        "❌ Название темы слишком длинное. Пожалуйста, отправьте более короткое название:"
    ),
    "teacher_enter_first_title": (
        "Тема: <b>{topic}</b>\n\n"
        "Теперь введи название <b>первого задания</b> внутри этой темы (например, 'Вопрос 1'):"
    ),
    "teacher_enter_title": "Тема: <b>{topic}</b>\n\nВведи название <b>задания</b>:",
    "teacher_enter_next_title": (
        "Тема: <b>{topic}</b>\n\nВведи название <b>следующего задания</b>:"
    ),
    "teacher_enter_title_again": "Тема: <b>{topic}</b>\n\nВведи название задания заново:",
    "teacher_title_too_long": (
        "❌ Название задания слишком длинное.\n"
        "Пожалуйста, отправьте более короткое название:"
    ),
    "teacher_enter_desc": "Напиши текстовое описание этого задания:",
    "teacher_enter_desc_with_title": (
        "Задание: <b>{title}</b>\n\nНапиши текстовое описание этого задания:"
    ),
    "teacher_send_media": (
        "Отправь файл с примером для этого задания.\n"
        "Если медиа не нужно, нажми «Пропустить»."
    ),
    "teacher_choose_answer_type": "В каком формате ученик должен отправить ответ на это задание?",
    "teacher_after_preview": (
        "✅ Предпросмотр завершен. В теме <b>«{topic}»</b> сейчас заданий: {count}.\n\n"
        "Что делаем дальше?"
    ),
    "teacher_task_added": (
        "✅ Задание <b>«{title}»</b> добавлено в тему <b>«{topic}»</b>.\n\n"
        "Что делаем дальше?"
    ),
    "teacher_preview_header": (
        "👀 <b>ПРЕДПРОСМОТР ТЕМЫ «{topic}»</b>\n"
        "<i>(Именно в таком виде это будет приходить ученику по очереди)</i>"
    ),
    "teacher_preview_item": (
        "📂 Тема: <b>{topic}</b>\n\n"
        "📝 <b>Задание {index}:</b> {title}\n\n"
        "{description}\n\n"
        "⚠️ Требуемый формат ответа: <b>{req_text}</b>"
    ),
    "teacher_select_groups_send": (
        "Тема: <b>{topic}</b> (Заданий: {count})\n\n"
        "Выбери классы и группы для отправки и нажми 'Отправить':"
    ),
    "teacher_select_at_least_one_group": "❗ Выберите хотя бы одну группу!",
    "teacher_topic_published": (
        "✅ Тема со всеми заданиями успешно создана и разослана выбранным группам!"
    ),
    "teacher_no_topics_to_delete": "У вас пока нет созданных заданий (тем).",
    "teacher_del_topic_pg": (
        "Выберите тему для удаления (Страница {page} из {total_pages}):\n\n"
        "<i>⚠️ Внимание: удаление темы навсегда сотрет все задания в ней "
        "и удалит ответы (прогресс) учеников.</i>"
    ),
    "teacher_del_topic_not_found": "Ошибка. Тема не найдена.",
    "teacher_del_topic_confirm": (
        "⚠️ Вы уверены, что хотите удалить тему <b>«{topic}»</b>?\n\n"
        "Это действие <b>необратимо</b>: все подзадания и отправленные ответы "
        "учеников будут удалены из системы."
    ),
    "teacher_del_topic_done": (
        "✅ Тема <b>«{topic}»</b> и все ответы к ней были успешно удалены."
    ),

    # ================= УЧИТЕЛЬ: ПРОВЕРКА И СТАТИСТИКА =================
    "teacher_check_groups_pg": (
        "Выберите группу для проверки (Страница {page} из {total_pages}):"
    ),
    "teacher_no_tasks_to_check": "Новых заданий на проверку пока нет.",
    "teacher_check_select_task": (
        "Группа: <b>{class_name} - {group_name}</b>\n"
        "Выберите задание для проверки:"
    ),
    "teacher_all_checked": "🎉 Все ответы к этому заданию уже проверены!",
    "teacher_check_task_caption": (
        "Тема: <b>{topic}</b>\n"
        "📝 <b>Задание:</b> {title}\n"
        "📖 <b>Описание:</b> {description}\n\n"
        "👇 <b>Выберите ученика для проверки:</b>"
    ),
    "teacher_sub_not_found": "Ошибка, ответ не найден.",
    "teacher_student_answer_header": "👤 <b>Ответ ученика:</b> {first_name} {last_name} (@{username})",
    "teacher_enter_grade": "Поставь оценку (от 1 до 5) отправив цифру:",
    "teacher_enter_comment": "Теперь напиши комментарий к оценке для ученика:",
    "teacher_invalid_grade": (
        "❌ Ошибка! Оценкой может быть только число от 1 до 5.\n\n"
        "Пожалуйста, отправьте корректную оценку:"
    ),
    "teacher_grade_saved": "✅ Оценка и комментарий сохранены!",
    "teacher_checked_groups_pg": (
        "👀 <b>Проверенные задания</b>\n"
        "Выберите группу (Стр. {page}/{total_pages}):"
    ),
    "teacher_checked_no_tasks": "В группе <b>{class_name} - {group_name}</b> нет заданий.",
    "teacher_checked_select_task": (
        "Группа: <b>{class_name} - {group_name}</b>\n"
        "Выберите задание для просмотра:"
    ),
    "teacher_checked_students_pg": (
        "📝 <b>Задание:</b> {title}\n"
        "Выберите ученика (Стр. {page}/{total_pages}):"
    ),
    "teacher_checked_not_submitted": "Работа данного ученика пока не проверена или еще не сдана.",
    "teacher_checked_sub_details": (
        "Тема: <b>{topic}</b>\n"
        "📝 <b>Задание:</b> {title}\n"
        "📖 <b>Описание:</b> {description}\n\n"
        "⭐️ <b>Оценка ученика:</b> {grade}\n"
        "👨‍🏫 <b>Ваш комментарий:</b> {comment}"
    ),
    "teacher_stats_groups_pg": (
        "Выберите группу для просмотра статистики (Страница {page} из {total_pages}):"
    ),
    "teacher_stats_group_header": "📊 <b>Статистика группы:</b> {class_name} - {group_name}\n\n",
    "teacher_stats_task_avg": "📝 {topic} | {title}: <b>{avg:.1f}</b>\n",
    "teacher_stats_task_empty": "📝 {topic} | {title}: <i>Нет оценок</i>\n",
    "teacher_stats_overall_avg": "\n📈 Общий средний балл: <b>{avg:.2f}</b>",
    "teacher_stats_overall_empty": "\n📈 Общий средний балл: <i>Нет оценок</i>",
    "teacher_stats_students_header": (
        "👥 <b>Ученики ({class_name} - {group_name})</b>\nВыберите ученика:"
    ),
    "teacher_stats_data_not_found": "Данные не найдены.",
    "teacher_stats_student_header": (
        "👤 <b>Успеваемость:</b> {first_name} {last_name}\n"
        "🏫 <b>Группа:</b> {class_name} - {group_name}\n\n"
    ),
    "teacher_stats_no_tasks": "<i>Нет заданий для этой группы.</i>",
    "teacher_stats_item_not_done": "📝 {topic} | {title}: ❌ <i>Не выполнено</i>\n",
    "teacher_stats_item_pending": "📝 {topic} | {title}: ⏳ <i>На проверке</i>\n",
    "teacher_stats_item_graded": "📝 {topic} | {title}: ⭐️ <b>{grade}</b>\n",

    # ================= АДМИН-ПАНЕЛЬ =================
    "admin_no_teachers": "В системе пока нет учителей.",
    "admin_teachers_pg": "👨‍🏫 <b>Список учителей</b> (Стр. {page}/{total_pages}):\nВыберите учителя:",
    "admin_teacher_no_classes": "У этого учителя пока нет классов.",
    "admin_classes_pg": "👨‍🏫 Учитель: <b>{teacher_name}</b>\n🏫 Выберите класс (Стр. {page}/{total_pages}):",
    "admin_class_not_found": "Ошибка: Класс не найден",
    "admin_class_no_groups": "В этом классе нет групп.",
    "admin_groups_pg": "🏫 Класс: <b>{class_name}</b>\n👥 Выберите группу (Стр. {page}/{total_pages}):",
    "admin_group_not_found": "Ошибка: Группа не найдена",
    "admin_group_no_students": "В группе <b>{group_name}</b> пока нет учеников.",
    "admin_students_pg": (
        "🏫 Класс: <b>{class_name}</b> | 👥 Группа: <b>{group_name}</b>\n"
        "Выберите ученика (Стр. {page}/{total_pages}):"
    ),
    "admin_student_not_found": "Ученик не найден",
    "admin_student_dossier": (
        "🔍 <b>Досье ученика:</b>\n"
        "Имя: {first_name} {last_name} (@{username})\n"
        "Статус: {status}\n"
        "🏫 Группа: {class_name} - {group_name}\n\n"
        "🔥 Дней подряд: {current_streak}\n"
        "✅ Всего решено заданий: {total_completed}\n"
        "🏆 Максимум заданий в день: {max_tasks_per_day}\n\n"
        "<b>Последние 3 выполненные задания:</b>\n"
    ),
    "admin_status_banned": "🚫 Забанен",
    "admin_status_active": "✅ Активен",
    "admin_no_answers": "<i>Пока нет ответов.</i>",
    "admin_no_other_users": "В базе данных пока нет других пользователей.",
    "admin_pm_list_pg": (
        "✉️ <b>Личные сообщения</b>\n"
        "Выберите пользователя для отправки сообщения (Стр. {page}/{total_pages}):"
    ),
    "admin_user_not_found": "Ошибка: Пользователь не найден.",
    "admin_pm_prompt": (
        "Напишите текст сообщения, которое будет отправлено пользователю:\n"
        "<b>{user_label}</b>"
    ),
    "admin_pm_received": "🔔 <b>Администратор отправил Вам личное сообщение:</b>\n\n{text}",
    "admin_pm_sent": "✅ Личное сообщение успешно доставлено!",
    "admin_pm_failed": (
        "❌ Ошибка при отправке. Возможно, пользователь заблокировал бота или удалил аккаунт."
    ),
    "admin_no_users": "Пользователей нет в базе данных.",
    "admin_actions_list_pg": (
        "🔍 <b>Действия пользователей</b>\n"
        "Выберите пользователя (Стр. {page}/{total_pages}):"
    ),
    "admin_user_dossier_header": (
        "🔍 <b>Досье на пользователя:</b>\n"
        "Имя: {first_name} {last_name} (@{username})\n"
        "Роль: <b>{role}</b>\n"
        "Статус: {status}\n\n"
    ),
    "admin_user_dossier_student": (
        "🏫 Группа: {class_name} - {group_name}\n"
        "🔥 Дней подряд: {current_streak}\n"
        "✅ Всего решено заданий: {total_completed}\n"
        "🏆 Максимум заданий в день: {max_tasks_per_day}\n\n"
        "<b>Последние выполненные задания:</b>\n"
    ),
    "admin_user_dossier_teacher": (
        "👥 Создано групп: <b>{groups_count}</b>\n"
        "📝 Создано заданий (всего шагов): <b>{tasks_count}</b>\n\n"
        "<b>Список групп:</b>\n"
    ),
    "admin_no_created_groups": "<i>Нет созданных групп.</i>",
    "admin_unlink_empty": "Нет учеников, привязанных к группам.",
    "admin_unlink_pg": (
        "✂️ <b>Отвязать от группы</b>\n"
        "Выберите ученика (Стр. {page}/{total_pages}):"
    ),
    "admin_unlink_done": "Ученик успешно отвязан от группы!",
    "admin_prompt_add_teacher": "Введите @юзернейм пользователя для назначения учителем:",
    "admin_prompt_add_admin": "Введите @юзернейм пользователя для назначения администратором:",
    "admin_prompt_rem_admin": "Введите @юзернейм для снятия роли администратора:",
    "admin_cannot_modify_founder": "❌ Нельзя изменять или блокировать пользователя с ролью FOUNDER.",
    "admin_prompt_rem_teacher": "Введите @юзернейм для снятия роли учителя:",
    "admin_prompt_ban": "Введите @юзернейм для бана:",
    "admin_prompt_unban": "Введите @юзернейм для разбана:",
    "admin_prompt_broad_student": "Напишите сообщение, которое будет отправлено <b>всем ученикам</b>:",
    "admin_prompt_broad_teacher": "Напишите сообщение, которое будет отправлено <b>всем учителям</b>:",
    "admin_broadcast_received": "🔔 <b>Уведомление от Администрации:</b>\n\n{text}",
    "admin_broadcast_done": "✅ Успешно!\nСообщение доставлено {count} пользователям с ролью '{target}'.",
    "admin_update_user_not_found": "❌ Пользователь @{username} не найден. Он должен нажать /start.",
    "admin_update_user_done": "✅ Данные пользователя @{username} обновлены!",

    # ================= КНОПКИ =================
    "btn_cancel": "❌ Отмена",
    "btn_back": "◀️ Назад",
    "btn_back_step": "⬅️ Шаг назад",
    "btn_back_to_menu": "◀️ В меню",
    "btn_home_menu": "🏠 В меню",
    "btn_prev_page": "⬅️ Пред.",
    "btn_next_page": "След. ➡️",

    # Регистрация
    "btn_role_student": "👨‍🎓 Я ученик",
    "btn_role_teacher": "👨‍🏫 Я учитель",
    "btn_reg_confirm": "✅ Всё верно",
    "btn_reg_edit": "🔄 Изменить",

    # Панель ученика
    "btn_s_new_tasks": "📝 Новые темы",
    "btn_s_progress": "⏳ В процессе",
    "btn_s_completed": "✅ Выполненные",
    "btn_s_profile": "👤 Мой профиль",
    "btn_s_edit_name": "✏️ Изменить имя",
    "btn_s_back_list": "◀️ К списку",
    "btn_s_exit_saved": "❌ Выйти в меню (Прогресс сохранен)",
    "btn_s_send_answer": "✅ Отправить учителю",
    "btn_s_retry_answer": "🔄 Записать заново",
    "btn_s_exit_menu": "❌ Выйти в меню",
    "btn_s_continue_topic": "Продолжить тему ➡️",
    "btn_s_pause_menu": "❌ Пауза (в меню)",
    "btn_s_return_menu": "🏠 Вернуться в меню",

    # Панель учителя
    "btn_t_new_task": "📝 Создать задание",
    "btn_t_del_task": "🗑 Удалить задание",
    "btn_t_resume_draft": "♻️ Продолжить черновик",
    "btn_t_check_tasks": "✅ Проверить ответы",
    "btn_t_checked_tasks": "👀 Проверенные",
    "btn_t_list_classes": "📋 Список классов",
    "btn_t_stats": "📊 Статистика",
    "btn_t_add_group": "➕ Создать группу",
    "btn_t_add_student": "👤 Добавить ученика",
    "btn_t_rem_student": "➖ Удалить ученика",
    "btn_t_back_groups": "◀️ К группам",
    "btn_t_back_to_groups": "◀️ Назад к группам",
    "btn_t_back_tasks": "◀️ К заданиям",
    "btn_t_back_students": "◀️ К списку учеников",
    "btn_t_back_task": "⬅️ Вернуться к заданию",
    "btn_t_skip_media": "⏭ Пропустить медиа",
    "btn_t_ans_audio": "🎤 Только Аудио",
    "btn_t_ans_video": "📹 Только Видео",
    "btn_t_ans_any": "🤷‍♂️ Любой формат",
    "btn_t_add_more": "➕ Ещё задание",
    "btn_t_remake_last": "✏️ Переделать",
    "btn_t_preview": "👀 Предпросмотр",
    "btn_t_select_groups": "➡️ Выбрать группы",
    "btn_t_postpone": "❌ Отложить",
    "btn_t_publish_topic": "🚀 Отправить ученикам",
    "btn_t_go_back": "⬅️ Вернуться назад",
    "btn_t_confirm_delete": "✅ Да, удалить навсегда",
    "btn_t_students_list": "👥 Список учеников",

    # Панель админа
    "btn_open_admin_panel": "🛠 Панель администратора",
    "btn_main_menu": "🏠 Главное меню",
    "btn_adm_add_admin": "👑 Назначить админа",
    "btn_adm_rem_admin": "🔻 Убрать админа",
    "btn_adm_add_teacher": "➕ Назначить учителя",
    "btn_adm_rem_teacher": "➖ Убрать учителя",
    "btn_adm_teachers": "👨‍🏫 Список учителей",
    "btn_adm_broad_student": "📢 Ученикам",
    "btn_adm_broad_teacher": "📢 Учителям",
    "btn_adm_pm": "✉️ Личное сообщение",
    "btn_adm_actions": "🔍 Действия",
    "btn_adm_unlink": "✂️ Отвязать от группы",
    "btn_adm_ban": "🔨 Забанить",
    "btn_adm_unban": "🕊 Разбанить",
    "btn_adm_back_panel": "◀️ В панель",
    "btn_adm_back_teachers": "◀️ К учителям",
    "btn_adm_back_classes": "◀️ К классам",
    "btn_adm_back_groups": "◀️ К группам",
    "btn_adm_back_students": "◀️ К списку учеников",
    "btn_adm_back_list": "◀️ Назад к списку",
}

LEXICON_CALLBACKS: dict[str, str] = {
    "s_panel": "Выход в меню",
    "s_profile": "Профиль",
    "s_tasks_new": "Новые темы",
    "s_tasks_progress": "В процессе",
    "s_completed": "Выполненные",
    "s_edit_name": "Смена имени",
    "reg_role_student": "Регистрация: выбор роли Ученик",
    "reg_role_teacher": "Регистрация: выбор роли Учитель",
    "reg_confirm": "Регистрация: Да",
    "reg_edit": "Регистрация: Изменить",
    "ans_send": "Отправка ответа",
    "ans_retry": "Перезапись",
    "t_menu": "Меню учителя",
    "t_new_task": "Создать задание",
    "t_del_task_start": "Удаление задания",
    "t_resume_draft": "К черновику",
    "t_check_tasks_0": "Проверка ответов",
    "t_chkd_pg_0": "Проверенные работы",
    "t_lc_pg_0": "Список классов",
    "t_st_pg_0": "Статистика",
    "t_add_group": "Создать группу",
    "t_add_student": "Добавить ученика",
    "t_rem_student": "Удалить ученика",
    "confirm_task": "Опубликовать тему",
    "admin_back": "Админ-панель",
    "admin_add_admin": "Назначить администратора",
    "admin_rem_admin": "Снять администратора",
    "admin_add_teacher": "Назначить учителя",
    "admin_rem_teacher": "Разжаловать учителя",
    "admin_broad_student": "Рассылка ученикам",
    "admin_broad_teacher": "Рассылка учителям",
    "admin_pml_0": "Личные сообщения",
    "adm_actl_0": "История действий",
    "adm_unl_0": "Отвязать от группы",
    "admin_ban": "Бан",
    "admin_unban": "Разбан",
}

LEXICON_CALLBACK_PREFIXES: tuple[tuple[str, str], ...] = (
    ("s_sub_", "Детали ответа"),
    ("s_do_t_", "Начать задание"),
    ("tg_group_", "Выбор группы"),
    ("t_chk_t_", "Выбор задания для проверки"),
    ("t_chk_s_", "Проверка ответа конкретного ученика"),
    ("adms_", "Профиль пользователя (админ)"),
    ("adm_actu_", "Просмотр истории действий"),
)
