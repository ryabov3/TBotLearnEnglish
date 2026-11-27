import React, { useState } from "react";
import { Flame, CheckCircle2, Trophy, Pencil } from "lucide-react";

import { apiFetch } from "../api/client";
import Modal from "../components/Modal";

const ROLE_LABELS = {
  student: "Ученик",
  teacher: "Учитель",
  admin: "Администратор",
  founder: "Основатель",
};

export default function ProfilePage({ user, onUpdated, notify }) {
  const [editOpen, setEditOpen] = useState(false);
  const [firstName, setFirstName] = useState(user.first_name || "");
  const [lastName, setLastName] = useState(user.last_name || "");
  const [saving, setSaving] = useState(false);

  const initials =
    ((user.first_name?.[0] || "") + (user.last_name?.[0] || "")).toUpperCase() || "U";

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await apiFetch("/api/me/profile", {
        method: "PATCH",
        body: JSON.stringify({ first_name: firstName, last_name: lastName }),
      });
      await onUpdated();
      setEditOpen(false);
      notify("✅ Профиль обновлён");
    } catch (err) {
      notify("❌ " + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="card card-hero">
        <div className="profile-head">
          <div className="avatar">{initials}</div>
          <div>
            <div className="card-title">
              {user.first_name} {user.last_name}
            </div>
            <div className="muted">
              @{user.username || "без_юзернейма"} · {ROLE_LABELS[user.role] || user.role}
            </div>
            <div className="muted">
              🏫 {user.class_name || "Нет класса"} / {user.group_name || "Нет группы"}
            </div>
          </div>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-block"
          onClick={() => {
            setFirstName(user.first_name || "");
            setLastName(user.last_name || "");
            setEditOpen(true);
          }}
        >
          <Pencil size={15} /> Изменить имя и фамилию
        </button>
      </div>

      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-value">
            <Flame size={19} color="#f59e0b" /> {user.current_streak}
          </div>
          <div className="kpi-label">Дней подряд</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">
            <CheckCircle2 size={19} color="#10b981" /> {user.total_completed}
          </div>
          <div className="kpi-label">Всего сдано</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-value">
            <Trophy size={19} color="#6366f1" /> {user.max_tasks_per_day}
          </div>
          <div className="kpi-label">Рекорд за день</div>
        </div>
      </div>

      <Modal open={editOpen} title="Редактировать профиль" onClose={() => setEditOpen(false)}>
        <form onSubmit={handleSave} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="field">
            <label>Имя (только буквы, 2–50 символов)</label>
            <input
              className="input"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Фамилия (только буквы, 2–50 символов)</label>
            <input
              className="input"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={saving}>
            {saving ? "Сохраняем..." : "Сохранить"}
          </button>
        </form>
      </Modal>
    </>
  );
}
