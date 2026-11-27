import React, { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Search } from "lucide-react";

import { apiFetch } from "../api/client";
import EmptyState from "../components/EmptyState";

const ROLE_LABELS = {
  student: "Ученик",
  teacher: "Учитель",
  admin: "Админ",
  founder: "Основатель",
};

export default function AdminPage({ currentUser, notify }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState("all");
  const [search, setSearch] = useState("");

  const isFounder = currentUser.role === "founder";

  const loadOverview = useCallback(async () => {
    try {
      const res = await apiFetch("/api/admin/overview");
      setData(res);
    } catch (e) {
      notify("❌ " + e.message);
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const handleUpdateUser = async (targetId, payload) => {
    try {
      await apiFetch(`/api/admin/users/${targetId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      notify("✅ Данные пользователя обновлены");
      await loadOverview();
    } catch (err) {
      notify("❌ " + err.message);
    }
  };

  const filteredUsers = useMemo(() => {
    if (!data) return [];
    const q = search.toLowerCase().trim();
    return data.users.filter((u) => {
      if (roleFilter !== "all" && u.role !== roleFilter) return false;
      if (!q) return true;
      const hay = `${u.first_name || ""} ${u.last_name || ""} ${u.username || ""} ${u.id}`.toLowerCase();
      return hay.includes(q);
    });
  }, [data, roleFilter, search]);

  if (loading || !data) {
    return (
      <div className="loader-wrap">
        <div className="spinner" />
      </div>
    );
  }

  const c = data.counts;

  return (
    <>
      <div className="section-header">
        <div className="section-title">🛠 Панель управления</div>
        {isFounder && <span className="badge badge-warning">👑 FOUNDER</span>}
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-value">{c.users}</div>
          <div className="kpi-label">Пользователей</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{c.teachers + c.admins + c.founders}</div>
          <div className="kpi-label">Учителей/Адм</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">{c.submissions}</div>
          <div className="kpi-label">Всего сдач</div>
        </div>
      </div>

      <div className="search-wrap">
        <Search size={16} />
        <input
          className="input"
          placeholder="Поиск по имени, @username или ID..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="pills">
        {[
          { id: "all", label: `Все (${c.users})` },
          { id: "student", label: `Ученики (${c.students})` },
          { id: "teacher", label: `Учителя (${c.teachers})` },
          { id: "admin", label: `Админы (${c.admins})` },
        ].map((p) => (
          <button
            key={p.id}
            type="button"
            className={`pill ${roleFilter === p.id ? "active" : ""}`}
            onClick={() => setRoleFilter(p.id)}
          >
            {p.label}
          </button>
        ))}
      </div>

      {!filteredUsers.length ? (
        <EmptyState icon="🔍" subtitle="Пользователи не найдены" />
      ) : (
        filteredUsers.map((u, idx) => {
          const isTargetFounder = u.role === "founder";
          const isTargetAdmin = u.role === "admin";
          const canModify = !isTargetFounder && (!isTargetAdmin || isFounder);

          return (
            <motion.div
              key={u.id}
              className="card"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(idx * 0.025, 0.25) }}
            >
              <div className="card-row">
                <div>
                  <div className="card-title">
                    {u.first_name || "Без имени"} {u.last_name || ""}
                  </div>
                  <div className="muted">
                    @{u.username || "нет"} · {u.class_name || "—"}/{u.group_name || "—"}
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <span className={`role-badge ${u.role}`}>{ROLE_LABELS[u.role] || u.role}</span>
                  {u.is_banned && <span className="badge badge-danger">БАН</span>}
                </div>
              </div>

              {canModify ? (
                <div className="btn-row">
                  {u.role === "student" && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleUpdateUser(u.id, { role: "teacher" })}
                    >
                      👨‍🏫 Сделать учителем
                    </button>
                  )}
                  {u.role === "teacher" && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleUpdateUser(u.id, { role: "student" })}
                    >
                      🎓 Снять учителя
                    </button>
                  )}
                  {isFounder && u.role !== "admin" && (
                    <button
                      type="button"
                      className="btn btn-success btn-sm"
                      onClick={() => handleUpdateUser(u.id, { role: "admin" })}
                    >
                      👑 Назначить админом
                    </button>
                  )}
                  {isFounder && u.role === "admin" && (
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleUpdateUser(u.id, { role: "student" })}
                    >
                      🔻 Снять админа
                    </button>
                  )}
                  {u.class_name && (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleUpdateUser(u.id, { unlink_group: true })}
                    >
                      ✂️ Отвязать
                    </button>
                  )}
                  <button
                    type="button"
                    className={`btn btn-sm ${u.is_banned ? "btn-success" : "btn-danger"}`}
                    onClick={() => handleUpdateUser(u.id, { is_banned: !u.is_banned })}
                  >
                    {u.is_banned ? "🕊 Разбанить" : "🔨 Бан"}
                  </button>
                </div>
              ) : (
                <div className="muted" style={{ fontSize: 12 }}>
                  🔒 Защищено правами роли
                </div>
              )}
            </motion.div>
          );
        })
      )}
    </>
  );
}
