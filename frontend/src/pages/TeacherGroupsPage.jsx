import React, { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plus, Trash2, UserPlus } from "lucide-react";

import { apiFetch } from "../api/client";
import EmptyState from "../components/EmptyState";
import Modal from "../components/Modal";

export default function TeacherGroupsPage({ notify }) {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [className, setClassName] = useState("");
  const [groupName, setGroupName] = useState("");

  const [selectedGroup, setSelectedGroup] = useState(null);
  const [students, setStudents] = useState([]);
  const [newUsername, setNewUsername] = useState("");

  const loadGroups = useCallback(async () => {
    try {
      const data = await apiFetch("/api/teacher/groups");
      setGroups(data.groups || []);
    } catch (e) {
      notify("❌ " + e.message);
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    loadGroups();
  }, [loadGroups]);

  const openGroup = async (groupId) => {
    try {
      const data = await apiFetch(`/api/teacher/groups/${groupId}/students`);
      setSelectedGroup(data.group);
      setStudents(data.students || []);
      setNewUsername("");
    } catch (e) {
      notify("❌ " + e.message);
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    try {
      await apiFetch("/api/teacher/groups", {
        method: "POST",
        body: JSON.stringify({ class_name: className, group_name: groupName }),
      });
      setCreateOpen(false);
      setClassName("");
      setGroupName("");
      notify("✅ Группа создана");
      await loadGroups();
    } catch (err) {
      notify("❌ " + err.message);
    }
  };

  const handleAddStudent = async (e) => {
    e.preventDefault();
    if (!selectedGroup || !newUsername.trim()) return;
    try {
      await apiFetch(`/api/teacher/groups/${selectedGroup.id}/students`, {
        method: "POST",
        body: JSON.stringify({ username: newUsername }),
      });
      notify("✅ Ученик добавлен");
      await openGroup(selectedGroup.id);
      await loadGroups();
    } catch (err) {
      notify("❌ " + err.message);
    }
  };

  const handleRemoveStudent = async (studentId) => {
    if (!selectedGroup) return;
    try {
      await apiFetch(`/api/teacher/groups/${selectedGroup.id}/students/${studentId}`, {
        method: "DELETE",
      });
      notify("Ученик удалён из группы");
      await openGroup(selectedGroup.id);
      await loadGroups();
    } catch (err) {
      notify("❌ " + err.message);
    }
  };

  if (loading) {
    return (
      <div className="loader-wrap">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <>
      <div className="section-header">
        <div className="section-title">👥 Классы и группы</div>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => setCreateOpen(true)}
        >
          <Plus size={15} /> Создать
        </button>
      </div>

      {!groups.length ? (
        <EmptyState icon="🏫" subtitle="У вас пока нет созданных классов" />
      ) : (
        groups.map((g, idx) => (
          <motion.div
            key={g.id}
            className="card"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.04 }}
          >
            <div className="card-row">
              <div>
                <div className="card-title">
                  📋 {g.class_name} — {g.group_name}
                </div>
                <div className="muted">
                  Учеников: {g.students_count} · Заданий: {g.tasks_count}
                </div>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => openGroup(g.id)}
              >
                Открыть
              </button>
            </div>
          </motion.div>
        ))
      )}

      <Modal open={createOpen} title="Новая учебная группа" onClose={() => setCreateOpen(false)}>
        <form onSubmit={handleCreateGroup} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="field">
            <label>Класс (например, 5А)</label>
            <input
              className="input"
              placeholder="5А"
              value={className}
              onChange={(e) => setClassName(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Группа (например, Группа 1)</label>
            <input
              className="input"
              placeholder="Группа 1"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary btn-block">
            Сохранить группу
          </button>
        </form>
      </Modal>

      <Modal
        open={Boolean(selectedGroup)}
        title={selectedGroup ? `${selectedGroup.class_name} — ${selectedGroup.group_name}` : ""}
        onClose={() => setSelectedGroup(null)}
      >
        <form onSubmit={handleAddStudent} className="card-row">
          <input
            className="input"
            placeholder="@username ученика"
            value={newUsername}
            onChange={(e) => setNewUsername(e.target.value)}
          />
          <button type="submit" className="btn btn-primary">
            <UserPlus size={16} />
          </button>
        </form>
        <div className="divider" />
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {students.length ? (
            students.map((s) => (
              <div key={s.id} className="sub-item card-row">
                <div>
                  <div style={{ fontSize: 14, fontWeight: 600 }}>
                    {s.first_name} {s.last_name}
                  </div>
                  <div className="muted" style={{ fontSize: 12 }}>
                    @{s.username || "нет"} · 🔥 {s.current_streak} · ✅ {s.total_completed}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  onClick={() => handleRemoveStudent(s.id)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          ) : (
            <p className="muted" style={{ textAlign: "center", padding: 12 }}>
              В группе пока нет учеников
            </p>
          )}
        </div>
      </Modal>
    </>
  );
}
