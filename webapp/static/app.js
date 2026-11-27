const tg = window.Telegram ? window.Telegram.WebApp : null;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = {
  user: null,
  botUsername: "",
  activeTab: "",
  studentTopicFilter: "new",
  teacherSubFilter: "pending",
  adminRoleFilter: "all",
  adminSearch: "",
  adminData: null,
};

const ROLE_LABELS = {
  student: "Ученик",
  teacher: "Учитель",
  admin: "Админ",
  founder: "Основатель",
};

const FORMAT_LABELS = {
  audio: "🎤 Только аудио",
  video: "📹 Только видео",
  any: "🤷‍♂️ Аудио или видео",
};

// ================= API =================
async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (tg && tg.initData) {
    headers["X-Telegram-Init-Data"] = tg.initData;
  }
  const res = await fetch(path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Ошибка сервера (${res.status})`);
  }
  return data;
}

function escapeHtml(str) {
  return String(str ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.remove("hidden");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add("hidden"), 2800);
}

function openModal(title, htmlContent) {
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = htmlContent;
  document.getElementById("modal-backdrop").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.add("hidden");
}

document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-backdrop").addEventListener("click", (e) => {
  if (e.target.id === "modal-backdrop") closeModal();
});

// ================= НАВИГАЦИЯ =================
function getTabsForRole(role) {
  if (role === "student") {
    return [
      { id: "student_topics", icon: "📚", label: "Темы" },
      { id: "student_subs", icon: "✅", label: "Сдачи" },
      { id: "profile", icon: "👤", label: "Профиль" },
    ];
  }
  const tabs = [
    { id: "teacher_groups", icon: "👥", label: "Классы" },
    { id: "teacher_topics", icon: "📝", label: "Задания" },
    { id: "teacher_check", icon: "✅", label: "Проверка" },
    { id: "teacher_stats", icon: "📊", label: "Статистика" },
    { id: "profile", icon: "👤", label: "Профиль" },
  ];
  if (role === "admin" || role === "founder") {
    tabs.push({ id: "admin", icon: "🛠", label: "Админ" });
  }
  return tabs;
}

function renderNav() {
  const nav = document.getElementById("bottom-nav");
  const tabs = getTabsForRole(state.user.role);
  nav.innerHTML = tabs
    .map(
      (t) => `
      <button class="nav-item ${state.activeTab === t.id ? "active" : ""}" data-tab="${t.id}">
        <span class="nav-icon">${t.icon}</span>
        <span>${t.label}</span>
      </button>`
    )
    .join("");
  nav.classList.remove("hidden");
  nav.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });
}

async function switchTab(tabId) {
  state.activeTab = tabId;
  renderNav();
  const container = document.getElementById("view-container");
  container.innerHTML = `<div class="loader-wrap"><div class="spinner"></div></div>`;

  try {
    if (tabId === "profile") await renderProfile(container);
    else if (tabId === "student_topics") await renderStudentTopics(container);
    else if (tabId === "student_subs") await renderStudentSubmissions(container);
    else if (tabId === "teacher_groups") await renderTeacherGroups(container);
    else if (tabId === "teacher_topics") await renderTeacherTopics(container);
    else if (tabId === "teacher_check") await renderTeacherCheck(container);
    else if (tabId === "teacher_stats") await renderTeacherStats(container);
    else if (tabId === "admin") await renderAdminPanel(container);
  } catch (err) {
    container.innerHTML = `
      <div class="card">
        <div class="card-title">⚠️ Ошибка загрузки</div>
        <p class="muted">${escapeHtml(err.message)}</p>
        <button class="btn btn-secondary" onclick="switchTab('${tabId}')">Повторить</button>
      </div>`;
  }
}

// ================= ПРОФИЛЬ =================
async function renderProfile(container) {
  const me = await api("/api/me");
  state.user = me.user;
  updateHeader();

  const u = state.user;
  const initials = ((u.first_name?.[0] || "") + (u.last_name?.[0] || "")).toUpperCase() || "U";

  container.innerHTML = `
    <div class="card card-hero">
      <div class="profile-head">
        <div class="avatar">${escapeHtml(initials)}</div>
        <div>
          <div class="card-title">${escapeHtml(u.first_name)} ${escapeHtml(u.last_name)}</div>
          <div class="muted">@${escapeHtml(u.username || "без_юзернейма")} · ${ROLE_LABELS[u.role] || u.role}</div>
          <div class="muted">🏫 ${escapeHtml(u.class_name || "Нет класса")} / ${escapeHtml(u.group_name || "Нет группы")}</div>
        </div>
      </div>
      <button id="btn-edit-profile" class="btn btn-secondary btn-block">✏️ Изменить имя и фамилию</button>
    </div>

    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-value">🔥 ${u.current_streak}</div>
        <div class="kpi-label">Дней подряд</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">✅ ${u.total_completed}</div>
        <div class="kpi-label">Всего сдано</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">🏆 ${u.max_tasks_per_day}</div>
        <div class="kpi-label">Рекорд за день</div>
      </div>
    </div>
  `;

  document.getElementById("btn-edit-profile").addEventListener("click", () => {
    openModal(
      "Редактировать профиль",
      `
      <div class="field">
        <label>Имя (только буквы, 2–50 символов)</label>
        <input id="inp-first-name" class="input" value="${escapeHtml(u.first_name || "")}" />
      </div>
      <div class="field">
        <label>Фамилия (только буквы, 2–50 символов)</label>
        <input id="inp-last-name" class="input" value="${escapeHtml(u.last_name || "")}" />
      </div>
      <button id="btn-save-profile" class="btn btn-primary btn-block">Сохранить</button>
      `
    );
    document.getElementById("btn-save-profile").addEventListener("click", async () => {
      try {
        const first_name = document.getElementById("inp-first-name").value;
        const last_name = document.getElementById("inp-last-name").value;
        await api("/api/me/profile", {
          method: "PATCH",
          body: JSON.stringify({ first_name, last_name }),
        });
        closeModal();
        showToast("✅ Профиль обновлён");
        await switchTab("profile");
      } catch (e) {
        showToast("❌ " + e.message);
      }
    });
  });
}

// ================= УЧЕНИК: ТЕМЫ =================
function openTaskInBot(taskId) {
  if (state.botUsername && tg && tg.openTelegramLink) {
    tg.openTelegramLink(`https://t.me/${state.botUsername}?start=task_${taskId}`);
    tg.close();
  } else {
    showToast("Откройте задание в чате бота для записи голоса или видео.");
    if (tg) tg.close();
  }
}

async function renderStudentTopics(container) {
  const data = await api("/api/student/topics");
  if (!data.has_group) {
    container.innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon">🏫</div>
        <div class="card-title">Вы ещё не добавлены в группу</div>
        <p class="muted">Попросите учителя добавить ваш @username в класс — после этого здесь появятся темы и задания.</p>
      </div>`;
    return;
  }

  const lists = {
    new: data.new_topics,
    progress: data.in_progress,
    done: data.completed_topics,
  };
  const currentList = lists[state.studentTopicFilter] || [];

  container.innerHTML = `
    <div class="section-header">
      <div class="section-title">📚 Мои темы</div>
      <span class="badge badge-accent">${escapeHtml(data.class_name)} · ${escapeHtml(data.group_name)}</span>
    </div>
    <div class="pills">
      <button class="pill ${state.studentTopicFilter === "new" ? "active" : ""}" data-f="new">🆕 Новые (${data.new_topics.length})</button>
      <button class="pill ${state.studentTopicFilter === "progress" ? "active" : ""}" data-f="progress">⏳ В процессе (${data.in_progress.length})</button>
      <button class="pill ${state.studentTopicFilter === "done" ? "active" : ""}" data-f="done">✅ Завершённые (${data.completed_topics.length})</button>
    </div>
    <div id="topics-list" style="display:flex;flex-direction:column;gap:12px;"></div>
  `;

  container.querySelectorAll(".pill").forEach((p) => {
    p.addEventListener("click", () => {
      state.studentTopicFilter = p.dataset.f;
      renderStudentTopics(container);
    });
  });

  const listEl = document.getElementById("topics-list");
  if (!currentList.length) {
    listEl.innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon">🎉</div>
        <div class="muted">В этом разделе пока пусто</div>
      </div>`;
    return;
  }

  listEl.innerHTML = currentList
    .map((topic) => {
      const pct = Math.round((topic.completed / Math.max(1, topic.total)) * 100);
      return `
        <div class="card">
          <div class="card-row">
            <div class="card-title">📂 ${escapeHtml(topic.topic)}</div>
            <span class="badge ${pct === 100 ? "badge-success" : "badge-accent"}">${topic.completed}/${topic.total}</span>
          </div>
          <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
          <div style="display:flex;flex-direction:column;gap:8px;margin-top:4px;">
            ${topic.tasks
              .map(
                (t) => `
              <div class="card-row" style="padding:8px 10px;background:var(--bg);border-radius:10px;">
                <div style="min-width:0;">
                  <div style="font-size:13px;font-weight:600;">${t.completed ? "✅" : "○"} ${escapeHtml(t.title)}</div>
                  <div class="muted" style="font-size:12px;">${FORMAT_LABELS[t.expected_answer] || t.expected_answer}</div>
                </div>
                ${
                  !t.completed
                    ? `<button class="btn btn-primary btn-sm" onclick="openTaskInBot(${t.id})">🎤 Сдать</button>`
                    : `<span class="badge badge-success">Сдано</span>`
                }
              </div>`
              )
              .join("")}
          </div>
        </div>`;
    })
    .join("");
}

// ================= УЧЕНИК: СДАЧИ =================
async function renderStudentSubmissions(container) {
  const data = await api("/api/student/submissions");
  if (!data.submissions.length) {
    container.innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon">📝</div>
        <div class="card-title">Пока нет выполненных заданий</div>
        <p class="muted">Выберите тему на вкладке «Темы» и отправьте свой первый ответ.</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="section-title">✅ История сдач</div>
    ${data.submissions
      .map(
        (s) => `
      <div class="card">
        <div class="card-row">
          <div>
            <div class="muted" style="font-size:12px;">${escapeHtml(s.topic)}</div>
            <div class="card-title">${escapeHtml(s.title)}</div>
          </div>
          ${
            s.grade
              ? `<span class="badge badge-success">⭐️ ${s.grade} / 5</span>`
              : `<span class="badge badge-warning">⏳ На проверке</span>`
          }
        </div>
        <p class="muted">${escapeHtml(s.description)}</p>
        ${
          s.teacher_comment
            ? `<div style="padding:9px 11px;background:var(--bg);border-radius:10px;font-size:13px;">
                 <b>👨‍🏫 Комментарий:</b> ${escapeHtml(s.teacher_comment)}
               </div>`
            : ""
        }
      </div>`
      )
      .join("")}
  `;
}

// ================= УЧИТЕЛЬ: КЛАССЫ И УЧЕНИКИ =================
async function renderTeacherGroups(container) {
  const data = await api("/api/teacher/groups");
  container.innerHTML = `
    <div class="section-header">
      <div class="section-title">👥 Классы и группы</div>
      <button id="btn-new-group" class="btn btn-primary btn-sm">➕ Создать</button>
    </div>
    <div id="groups-list" style="display:flex;flex-direction:column;gap:12px;"></div>
  `;

  document.getElementById("btn-new-group").addEventListener("click", () => {
    openModal(
      "Новая учебная группа",
      `
      <div class="field">
        <label>Класс (например, 5А)</label>
        <input id="inp-class-name" class="input" placeholder="5А" />
      </div>
      <div class="field">
        <label>Группа (например, Группа 1)</label>
        <input id="inp-group-name" class="input" placeholder="Группа 1" />
      </div>
      <button id="btn-create-group-submit" class="btn btn-primary btn-block">Сохранить группу</button>
      `
    );
    document.getElementById("btn-create-group-submit").addEventListener("click", async () => {
      try {
        const class_name = document.getElementById("inp-class-name").value;
        const group_name = document.getElementById("inp-group-name").value;
        await api("/api/teacher/groups", {
          method: "POST",
          body: JSON.stringify({ class_name, group_name }),
        });
        closeModal();
        showToast("✅ Группа создана");
        await switchTab("teacher_groups");
      } catch (e) {
        showToast("❌ " + e.message);
      }
    });
  });

  const listEl = document.getElementById("groups-list");
  if (!data.groups.length) {
    listEl.innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon">🏫</div>
        <div class="muted">У вас пока нет созданных классов</div>
      </div>`;
    return;
  }

  listEl.innerHTML = data.groups
    .map(
      (g) => `
      <div class="card">
        <div class="card-row">
          <div>
            <div class="card-title">📋 ${escapeHtml(g.class_name)} — ${escapeHtml(g.group_name)}</div>
            <div class="muted">Учеников: ${g.students_count} · Заданий: ${g.tasks_count}</div>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="openGroupModal(${g.id})">Открыть</button>
        </div>
      </div>`
    )
    .join("");
}

window.openGroupModal = async function (groupId) {
  try {
    const data = await api(`/api/teacher/groups/${groupId}/students`);
    const g = data.group;
    openModal(
      `${g.class_name} — ${g.group_name}`,
      `
      <div class="card-row">
        <input id="inp-add-student" class="input" placeholder="@username ученика" />
        <button id="btn-add-student-go" class="btn btn-primary">➕</button>
      </div>
      <div class="divider"></div>
      <div style="display:flex;flex-direction:column;gap:8px;">
        ${
          data.students.length
            ? data.students
                .map(
                  (s) => `
              <div class="card-row" style="padding:8px 10px;background:var(--bg);border-radius:10px;">
                <div>
                  <div style="font-size:14px;font-weight:600;">${escapeHtml(s.first_name)} ${escapeHtml(s.last_name)}</div>
                  <div class="muted" style="font-size:12px;">@${escapeHtml(s.username || "нет")} · 🔥 ${s.current_streak} · ✅ ${s.total_completed}</div>
                </div>
                <button class="btn btn-danger btn-sm" onclick="removeStudentFromGroup(${groupId}, ${s.id})">Удалить</button>
              </div>`
                )
                .join("")
            : `<div class="muted" style="text-align:center;padding:12px;">В группе пока нет учеников</div>`
        }
      </div>
      `
    );

    document.getElementById("btn-add-student-go").addEventListener("click", async () => {
      try {
        const username = document.getElementById("inp-add-student").value;
        await api(`/api/teacher/groups/${groupId}/students`, {
          method: "POST",
          body: JSON.stringify({ username }),
        });
        showToast("✅ Ученик добавлен");
        await openGroupModal(groupId);
        await renderTeacherGroups(document.getElementById("view-container"));
      } catch (e) {
        showToast("❌ " + e.message);
      }
    });
  } catch (e) {
    showToast("❌ " + e.message);
  }
};

window.removeStudentFromGroup = async function (groupId, studentId) {
  try {
    await api(`/api/teacher/groups/${groupId}/students/${studentId}`, { method: "DELETE" });
    showToast("Ученик удалён из группы");
    await openGroupModal(groupId);
    await renderTeacherGroups(document.getElementById("view-container"));
  } catch (e) {
    showToast("❌ " + e.message);
  }
};

// ================= УЧИТЕЛЬ: ЗАДАНИЯ =================
async function renderTeacherTopics(container) {
  const [topicsData, groupsData] = await Promise.all([
    api("/api/teacher/topics"),
    api("/api/teacher/groups"),
  ]);

  container.innerHTML = `
    <div class="section-header">
      <div class="section-title">📝 Мои темы</div>
      <button id="btn-new-topic" class="btn btn-primary btn-sm">➕ Создать тему</button>
    </div>
    <div id="teacher-topics-list" style="display:flex;flex-direction:column;gap:12px;"></div>
  `;

  document.getElementById("btn-new-topic").addEventListener("click", () => {
    if (!groupsData.groups.length) {
      showToast("Сначала создайте хотя бы одну группу на вкладке «Классы».");
      return;
    }
    openCreateTopicModal(groupsData.groups);
  });

  const listEl = document.getElementById("teacher-topics-list");
  if (!topicsData.topics.length) {
    listEl.innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon">📝</div>
        <div class="muted">Созданных тем пока нет</div>
      </div>`;
    return;
  }

  listEl.innerHTML = topicsData.topics
    .map(
      (t) => `
      <div class="card">
        <div class="card-row">
          <div>
            <div class="card-title">📂 ${escapeHtml(t.topic)}</div>
            <div class="muted">Заданий: ${t.tasks_count} · Группы: ${escapeHtml(t.groups.join(", "))}</div>
          </div>
          <button class="btn btn-danger btn-sm" data-del-topic="${escapeHtml(t.topic)}">🗑</button>
        </div>
      </div>`
    )
    .join("");

  listEl.querySelectorAll("[data-del-topic]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const topic = btn.dataset.delTopic;
      if (!confirm(`Удалить тему «${topic}» и все ответы учеников?`)) return;
      try {
        await api(`/api/teacher/topics/${encodeURIComponent(topic)}`, { method: "DELETE" });
        showToast("🗑 Тема удалена");
        await switchTab("teacher_topics");
      } catch (e) {
        showToast("❌ " + e.message);
      }
    });
  });
}

function openCreateTopicModal(groups) {
  const selectedGroupIds = new Set();
  let taskBlocks = [{ title: "", description: "", expected_answer: "any" }];

  function renderModal() {
    openModal(
      "Новая тема с заданиями",
      `
      <div class="field">
        <label>Название темы</label>
        <input id="inp-topic-name" class="input" placeholder="Например: Hobbies" value="${escapeHtml(document.getElementById("inp-topic-name")?.value || "")}" />
      </div>
      <div class="field">
        <label>Выберите группы для отправки</label>
        <div id="topic-group-chips" class="chip-group">
          ${groups
            .map(
              (g) => `
            <button type="button" class="chip ${selectedGroupIds.has(g.id) ? "selected" : ""}" data-gid="${g.id}">
              ${selectedGroupIds.has(g.id) ? "✅ " : ""}${escapeHtml(g.class_name)} - ${escapeHtml(g.group_name)}
            </button>`
            )
            .join("")}
        </div>
      </div>
      <div class="divider"></div>
      <div id="topic-tasks-wrap" style="display:flex;flex-direction:column;gap:10px;">
        ${taskBlocks
          .map(
            (tb, idx) => `
          <div class="card" style="background:var(--bg);padding:12px;">
            <div class="card-row">
              <strong style="font-size:13px;">Задание #${idx + 1}</strong>
              ${taskBlocks.length > 1 ? `<button type="button" class="btn btn-danger btn-sm" data-rm-task="${idx}">Убрать</button>` : ""}
            </div>
            <input class="input" data-tf-title="${idx}" placeholder="Название задания" value="${escapeHtml(tb.title)}" />
            <textarea class="textarea" data-tf-desc="${idx}" placeholder="Описание задания...">${escapeHtml(tb.description)}</textarea>
            <select class="select" data-tf-fmt="${idx}">
              <option value="any" ${tb.expected_answer === "any" ? "selected" : ""}>🤷‍♂️ Любой формат (Аудио или Видео)</option>
              <option value="audio" ${tb.expected_answer === "audio" ? "selected" : ""}>🎤 Только Аудио/Голосовое</option>
              <option value="video" ${tb.expected_answer === "video" ? "selected" : ""}>📹 Только Видео/Кружок</option>
            </select>
          </div>`
          )
          .join("")}
      </div>
      <div class="btn-row">
        <button type="button" id="btn-add-subtask" class="btn btn-secondary" style="flex:1;">➕ Ещё задание</button>
        <button type="button" id="btn-publish-topic" class="btn btn-primary" style="flex:1;">🚀 Опубликовать</button>
      </div>
      `
    );

    const syncInputs = () => {
      taskBlocks.forEach((tb, idx) => {
        tb.title = document.querySelector(`[data-tf-title="${idx}"]`)?.value || "";
        tb.description = document.querySelector(`[data-tf-desc="${idx}"]`)?.value || "";
        tb.expected_answer = document.querySelector(`[data-tf-fmt="${idx}"]`)?.value || "any";
      });
    };

    document.querySelectorAll("#topic-group-chips .chip").forEach((ch) => {
      ch.addEventListener("click", () => {
        syncInputs();
        const gid = Number(ch.dataset.gid);
        if (selectedGroupIds.has(gid)) selectedGroupIds.delete(gid);
        else selectedGroupIds.add(gid);
        renderModal();
      });
    });

    document.querySelectorAll("[data-rm-task]").forEach((btn) => {
      btn.addEventListener("click", () => {
        syncInputs();
        taskBlocks.splice(Number(btn.dataset.rmTask), 1);
        renderModal();
      });
    });

    document.getElementById("btn-add-subtask").addEventListener("click", () => {
      syncInputs();
      taskBlocks.push({ title: "", description: "", expected_answer: "any" });
      renderModal();
    });

    document.getElementById("btn-publish-topic").addEventListener("click", async () => {
      syncInputs();
      const topic = document.getElementById("inp-topic-name").value.trim();
      if (!topic) return showToast("Введите название темы");
      if (!selectedGroupIds.size) return showToast("Выберите хотя бы одну группу");
      if (taskBlocks.some((t) => !t.title.trim() || !t.description.trim())) {
        return showToast("Заполните название и описание всех заданий");
      }
      try {
        await api("/api/teacher/topics", {
          method: "POST",
          body: JSON.stringify({
            topic,
            group_ids: Array.from(selectedGroupIds),
            tasks: taskBlocks,
          }),
        });
        closeModal();
        showToast("✅ Тема опубликована!");
        await switchTab("teacher_topics");
      } catch (e) {
        showToast("❌ " + e.message);
      }
    });
  }

  renderModal();
}

// ================= УЧИТЕЛЬ: ПРОВЕРКА ОТВЕТОВ =================
async function renderTeacherCheck(container) {
  const data = await api(`/api/teacher/submissions?status_filter=${state.teacherSubFilter}`);
  container.innerHTML = `
    <div class="section-title">✅ Проверка ответов</div>
    <div class="pills">
      <button class="pill ${state.teacherSubFilter === "pending" ? "active" : ""}" data-sf="pending">⏳ На проверке</button>
      <button class="pill ${state.teacherSubFilter === "graded" ? "active" : ""}" data-sf="graded">✅ Проверенные</button>
    </div>
    <div id="subs-check-list" style="display:flex;flex-direction:column;gap:12px;"></div>
  `;

  container.querySelectorAll(".pill").forEach((p) => {
    p.addEventListener("click", () => {
      state.teacherSubFilter = p.dataset.sf;
      renderTeacherCheck(container);
    });
  });

  const listEl = document.getElementById("subs-check-list");
  if (!data.submissions.length) {
    listEl.innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon">🎉</div>
        <div class="muted">${state.teacherSubFilter === "pending" ? "Все ответы проверены!" : "Проверенных работ пока нет"}</div>
      </div>`;
    return;
  }

  listEl.innerHTML = data.submissions
    .map(
      (s) => `
      <div class="card">
        <div class="card-row">
          <div>
            <div class="card-title">👤 ${escapeHtml(s.student_name)}</div>
            <div class="muted">${escapeHtml(s.class_name)} - ${escapeHtml(s.group_name)} · ${escapeHtml(s.topic)} | ${escapeHtml(s.title)}</div>
          </div>
          ${
            s.grade
              ? `<span class="badge badge-success">⭐️ ${s.grade}</span>`
              : `<span class="badge badge-warning">⏳ Ждёт</span>`
          }
        </div>
        ${
          s.teacher_comment
            ? `<div class="muted">Комментарий: ${escapeHtml(s.teacher_comment)}</div>`
            : ""
        }
        <button class="btn btn-primary btn-sm" onclick="openGradeModal(${s.id}, ${s.grade || 5}, '${escapeHtml(s.teacher_comment || "").replaceAll("'", "\\'")}')">
          ${s.grade ? "✏️ Изменить оценку" : "⭐️ Оценить работу"}
        </button>
      </div>`
    )
    .join("");
}

window.openGradeModal = function (subId, currentGrade, currentComment) {
  let selectedGrade = currentGrade || 5;
  openModal(
    "Оценка работы",
    `
    <div class="field">
      <label>Оценка (1–5)</label>
      <div id="grade-picker" class="grade-picker">
        ${[1, 2, 3, 4, 5]
          .map(
            (g) => `<button type="button" class="grade-btn ${g === selectedGrade ? "selected" : ""}" data-g="${g}">${g}</button>`
          )
          .join("")}
      </div>
    </div>
    <div class="field">
      <label>Комментарий ученику</label>
      <textarea id="inp-grade-comment" class="textarea" placeholder="Отличное произношение!">${escapeHtml(currentComment || "")}</textarea>
    </div>
    <button id="btn-save-grade" class="btn btn-primary btn-block">Сохранить оценку</button>
    `
  );

  document.querySelectorAll("#grade-picker .grade-btn").forEach((b) => {
    b.addEventListener("click", () => {
      selectedGrade = Number(b.dataset.g);
      document.querySelectorAll("#grade-picker .grade-btn").forEach((x) => x.classList.remove("selected"));
      b.classList.add("selected");
    });
  });

  document.getElementById("btn-save-grade").addEventListener("click", async () => {
    try {
      const comment = document.getElementById("inp-grade-comment").value;
      await api(`/api/teacher/submissions/${subId}/grade`, {
        method: "POST",
        body: JSON.stringify({ grade: selectedGrade, comment }),
      });
      closeModal();
      showToast("✅ Оценка сохранена");
      await switchTab("teacher_check");
    } catch (e) {
      showToast("❌ " + e.message);
    }
  });
};

// ================= УЧИТЕЛЬ: СТАТИСТИКА =================
async function renderTeacherStats(container) {
  const groupsData = await api("/api/teacher/groups");
  if (!groupsData.groups.length) {
    container.innerHTML = `<div class="card empty-state"><div class="empty-icon">📊</div><div class="muted">Сначала создайте группу</div></div>`;
    return;
  }

  container.innerHTML = `
    <div class="section-title">📊 Статистика по группам</div>
    <div class="pills" id="stats-group-pills">
      ${groupsData.groups
        .map(
          (g, i) => `<button class="pill ${i === 0 ? "active" : ""}" data-sgid="${g.id}">${escapeHtml(g.class_name)} - ${escapeHtml(g.group_name)}</button>`
        )
        .join("")}
    </div>
    <div id="stats-content"><div class="loader-wrap"><div class="spinner"></div></div></div>
  `;

  const loadGroupStats = async (gid) => {
    const sc = document.getElementById("stats-content");
    sc.innerHTML = `<div class="loader-wrap"><div class="spinner"></div></div>`;
    const st = await api(`/api/teacher/groups/${gid}/stats`);
    sc.innerHTML = `
      <div class="kpi-grid cols-2">
        <div class="kpi-card">
          <div class="kpi-value">${st.overall_avg !== null ? "⭐️ " + st.overall_avg : "—"}</div>
          <div class="kpi-label">Общий средний балл</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-value">${st.students.length}</div>
          <div class="kpi-label">Учеников в группе</div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">📝 Средний балл по заданиям</div>
        ${
          st.tasks.length
            ? st.tasks
                .map((t) => {
                  const pct = t.avg ? Math.round((t.avg / 5) * 100) : 0;
                  return `
                    <div>
                      <div class="card-row" style="margin-bottom:4px;">
                        <span style="font-size:13px;">${escapeHtml(t.topic)} · ${escapeHtml(t.title)}</span>
                        <strong style="font-size:13px;">${t.avg !== null ? t.avg : "—"}</strong>
                      </div>
                      <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
                    </div>`;
                })
                .join("")
            : `<div class="muted">Заданий пока нет</div>`
        }
      </div>

      <div class="card">
        <div class="card-title">👥 Успеваемость учеников</div>
        ${
          st.students.length
            ? st.students
                .map(
                  (s) => `
                <div class="card-row" style="padding:8px 10px;background:var(--bg);border-radius:10px;">
                  <div>
                    <div style="font-size:14px;font-weight:600;">${escapeHtml(s.name)}</div>
                    <div class="muted" style="font-size:12px;">🔥 ${s.current_streak} дн. · ✅ ${s.total_completed} сдач</div>
                  </div>
                  <span class="badge ${s.avg >= 4 ? "badge-success" : "badge-accent"}">${s.avg !== null ? "⭐️ " + s.avg : "Нет оценок"}</span>
                </div>`
                )
                .join("")
            : `<div class="muted">Учеников пока нет</div>`
        }
      </div>
    `;
  };

  container.querySelectorAll("#stats-group-pills .pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      container.querySelectorAll("#stats-group-pills .pill").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      loadGroupStats(Number(btn.dataset.sgid));
    });
  });

  await loadGroupStats(groupsData.groups[0].id);
}

// ================= АДМИН И FOUNDER =================
async function renderAdminPanel(container) {
  const data = await api("/api/admin/overview");
  state.adminData = data;
  const c = data.counts;
  const isFounder = state.user.role === "founder";

  container.innerHTML = `
    <div class="section-header">
      <div class="section-title">🛠 Панель управления</div>
      ${isFounder ? `<span class="badge badge-warning">👑 FOUNDER</span>` : ""}
    </div>

    <div class="kpi-grid">
      <div class="kpi-card"><div class="kpi-value">${c.users}</div><div class="kpi-label">Пользователей</div></div>
      <div class="kpi-card"><div class="kpi-value">${c.teachers + c.admins + c.founders}</div><div class="kpi-label">Учителей/Адм</div></div>
      <div class="kpi-card"><div class="kpi-value">${c.submissions}</div><div class="kpi-label">Всего сдач</div></div>
    </div>

    <input id="admin-search" class="input" placeholder="🔍 Поиск по имени или @username..." value="${escapeHtml(state.adminSearch)}" />

    <div class="pills" id="admin-role-pills">
      <button class="pill ${state.adminRoleFilter === "all" ? "active" : ""}" data-rf="all">Все (${c.users})</button>
      <button class="pill ${state.adminRoleFilter === "student" ? "active" : ""}" data-rf="student">Ученики (${c.students})</button>
      <button class="pill ${state.adminRoleFilter === "teacher" ? "active" : ""}" data-rf="teacher">Учителя (${c.teachers})</button>
      <button class="pill ${state.adminRoleFilter === "admin" ? "active" : ""}" data-rf="admin">Админы (${c.admins})</button>
    </div>

    <div id="admin-users-list" style="display:flex;flex-direction:column;gap:10px;"></div>
  `;

  const renderUsersList = () => {
    const q = state.adminSearch.toLowerCase().trim();
    const filtered = state.adminData.users.filter((u) => {
      if (state.adminRoleFilter !== "all" && u.role !== state.adminRoleFilter) return false;
      if (!q) return true;
      const hay = `${u.first_name || ""} ${u.last_name || ""} ${u.username || ""} ${u.id}`.toLowerCase();
      return hay.includes(q);
    });

    const listEl = document.getElementById("admin-users-list");
    if (!filtered.length) {
      listEl.innerHTML = `<div class="card empty-state"><div class="muted">Пользователи не найдены</div></div>`;
      return;
    }

    listEl.innerHTML = filtered
      .map((u) => {
        const isTargetFounder = u.role === "founder";
        const isTargetAdmin = u.role === "admin";
        const canModify = !isTargetFounder && (!isTargetAdmin || isFounder);

        return `
          <div class="card">
            <div class="card-row">
              <div>
                <div class="card-title">${escapeHtml(u.first_name || "Без имени")} ${escapeHtml(u.last_name || "")}</div>
                <div class="muted">@${escapeHtml(u.username || "нет")} · ${escapeHtml(u.class_name || "—")}/${escapeHtml(u.group_name || "—")}</div>
              </div>
              <div style="display:flex;gap:6px;align-items:center;">
                <span class="role-badge ${u.role}">${ROLE_LABELS[u.role] || u.role}</span>
                ${u.is_banned ? `<span class="badge badge-danger">БАН</span>` : ""}
              </div>
            </div>
            ${
              canModify
                ? `<div class="btn-row">
                    ${
                      u.role === "student"
                        ? `<button class="btn btn-secondary btn-sm" onclick="adminUpdateUser(${u.id}, {role:'teacher'})">👨‍🏫 Сделать учителем</button>`
                        : u.role === "teacher"
                        ? `<button class="btn btn-secondary btn-sm" onclick="adminUpdateUser(${u.id}, {role:'student'})">🎓 Снять учителя</button>`
                        : ""
                    }
                    ${
                      isFounder && u.role !== "admin"
                        ? `<button class="btn btn-success btn-sm" onclick="adminUpdateUser(${u.id}, {role:'admin'})">👑 Назначить админом</button>`
                        : isFounder && u.role === "admin"
                        ? `<button class="btn btn-danger btn-sm" onclick="adminUpdateUser(${u.id}, {role:'student'})">🔻 Снять админа</button>`
                        : ""
                    }
                    ${
                      u.class_name
                        ? `<button class="btn btn-secondary btn-sm" onclick="adminUpdateUser(${u.id}, {unlink_group:true})">✂️ Отвязать</button>`
                        : ""
                    }
                    <button class="btn ${u.is_banned ? "btn-success" : "btn-danger"} btn-sm" onclick="adminUpdateUser(${u.id}, {is_banned:${!u.is_banned}})">
                      ${u.is_banned ? "🕊 Разбанить" : "🔨 Бан"}
                    </button>
                  </div>`
                : `<div class="muted" style="font-size:12px;">🔒 Защищено правами роли</div>`
            }
          </div>`;
      })
      .join("");
  };

  document.getElementById("admin-search").addEventListener("input", (e) => {
    state.adminSearch = e.target.value;
    renderUsersList();
  });

  container.querySelectorAll("#admin-role-pills .pill").forEach((p) => {
    p.addEventListener("click", () => {
      state.adminRoleFilter = p.dataset.rf;
      container.querySelectorAll("#admin-role-pills .pill").forEach((x) => x.classList.remove("active"));
      p.classList.add("active");
      renderUsersList();
    });
  });

  renderUsersList();
}

window.adminUpdateUser = async function (targetId, payload) {
  try {
    await api(`/api/admin/users/${targetId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    showToast("✅ Данные пользователя обновлены");
    await switchTab("admin");
  } catch (e) {
    showToast("❌ " + e.message);
  }
};

// ================= СТАРТ ПРИЛОЖЕНИЯ =================
function updateHeader() {
  const u = state.user;
  document.getElementById("user-subtitle").textContent = `${u.first_name || ""} ${u.last_name || ""}`.trim();
  const badge = document.getElementById("role-badge");
  badge.textContent = ROLE_LABELS[u.role] || u.role;
  badge.className = `role-badge ${u.role}`;
}

async function init() {
  try {
    const me = await api("/api/me");
    state.user = me.user;
    state.botUsername = me.bot_username || "";
    updateHeader();
    const defaultTab = state.user.role === "student" ? "student_topics" : "teacher_groups";
    await switchTab(defaultTab);
  } catch (err) {
    document.getElementById("user-subtitle").textContent = "Доступ ограничен";
    document.getElementById("role-badge").textContent = "—";
    document.getElementById("view-container").innerHTML = `
      <div class="card empty-state">
        <div class="empty-icon">🔒</div>
        <div class="card-title">Не удалось войти</div>
        <p class="muted">${escapeHtml(err.message)}</p>
      </div>`;
  }
}

init();
