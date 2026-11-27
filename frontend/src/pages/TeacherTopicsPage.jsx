import React, { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Plus, Trash2, Send } from "lucide-react";

import { apiFetch } from "../api/client";
import EmptyState from "../components/EmptyState";
import Modal from "../components/Modal";

const emptyTask = () => ({ title: "", description: "", expected_answer: "any" });

export default function TeacherTopicsPage({ notify }) {
  const [topics, setTopics] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);

  const [createOpen, setCreateOpen] = useState(false);
  const [topicName, setTopicName] = useState("");
  const [selectedGroupIds, setSelectedGroupIds] = useState([]);
  const [taskBlocks, setTaskBlocks] = useState([emptyTask()]);
  const [saving, setSaving] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [tRes, gRes] = await Promise.all([
        apiFetch("/api/teacher/topics"),
        apiFetch("/api/teacher/groups"),
      ]);
      setTopics(tRes.topics || []);
      setGroups(gRes.groups || []);
    } catch (e) {
      notify("❌ " + e.message);
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const toggleGroup = (gid) => {
    setSelectedGroupIds((prev) =>
      prev.includes(gid) ? prev.filter((id) => id !== gid) : [...prev, gid]
    );
  };

  const updateTask = (idx, field, val) => {
    setTaskBlocks((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, [field]: val } : item))
    );
  };

  const handlePublish = async (e) => {
    e.preventDefault();
    if (!topicName.trim()) return notify("Введите название темы");
    if (!selectedGroupIds.length) return notify("Выберите хотя бы одну группу");
    if (taskBlocks.some((t) => !t.title.trim() || !t.description.trim())) {
      return notify("Заполните название и описание всех заданий");
    }
    setSaving(true);
    try {
      await apiFetch("/api/teacher/topics", {
        method: "POST",
        body: JSON.stringify({
          topic: topicName,
          group_ids: selectedGroupIds,
          tasks: taskBlocks,
        }),
      });
      setCreateOpen(false);
      setTopicName("");
      setSelectedGroupIds([]);
      setTaskBlocks([emptyTask()]);
      notify("✅ Тема опубликована!");
      await loadData();
    } catch (err) {
      notify("❌ " + err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (topic) => {
    if (!window.confirm(`Удалить тему «${topic}» и все ответы учеников?`)) return;
    try {
      await apiFetch(`/api/teacher/topics/${encodeURIComponent(topic)}`, {
        method: "DELETE",
      });
      notify("🗑 Тема удалена");
      await loadData();
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
        <div className="section-title">📝 Мои темы</div>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => {
            if (!groups.length) return notify("Сначала создайте группу на вкладке «Классы».");
            setCreateOpen(true);
          }}
        >
          <Plus size={15} /> Создать тему
        </button>
      </div>

      {!topics.length ? (
        <EmptyState icon="📝" subtitle="Созданных тем пока нет" />
      ) : (
        topics.map((t, idx) => (
          <motion.div
            key={t.topic}
            className="card"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.04 }}
          >
            <div className="card-row">
              <div>
                <div className="card-title">📂 {t.topic}</div>
                <div className="muted">
                  Заданий: {t.tasks_count} · Группы: {t.groups.join(", ")}
                </div>
              </div>
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={() => handleDelete(t.topic)}
              >
                <Trash2 size={14} />
              </button>
            </div>
          </motion.div>
        ))
      )}

      <Modal open={createOpen} title="Новая тема с заданиями" onClose={() => setCreateOpen(false)}>
        <form onSubmit={handlePublish} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="field">
            <label>Название темы</label>
            <input
              className="input"
              placeholder="Например: Hobbies"
              value={topicName}
              onChange={(e) => setTopicName(e.target.value)}
            />
          </div>

          <div className="field">
            <label>Выберите группы для отправки</label>
            <div className="chip-group">
              {groups.map((g) => {
                const active = selectedGroupIds.includes(g.id);
                return (
                  <button
                    key={g.id}
                    type="button"
                    className={`chip ${active ? "selected" : ""}`}
                    onClick={() => toggleGroup(g.id)}
                  >
                    {active ? "✅ " : ""}
                    {g.class_name} - {g.group_name}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="divider" />

          {taskBlocks.map((tb, idx) => (
            <div key={idx} className="sub-item" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div className="card-row">
                <strong style={{ fontSize: 13 }}>Задание #{idx + 1}</strong>
                {taskBlocks.length > 1 && (
                  <button
                    type="button"
                    className="btn btn-danger btn-sm"
                    onClick={() => setTaskBlocks((p) => p.filter((_, i) => i !== idx))}
                  >
                    Убрать
                  </button>
                )}
              </div>
              <input
                className="input"
                placeholder="Название задания"
                value={tb.title}
                onChange={(e) => updateTask(idx, "title", e.target.value)}
              />
              <textarea
                className="textarea"
                placeholder="Описание задания..."
                value={tb.description}
                onChange={(e) => updateTask(idx, "description", e.target.value)}
              />
              <select
                className="select"
                value={tb.expected_answer}
                onChange={(e) => updateTask(idx, "expected_answer", e.target.value)}
              >
                <option value="any">🤷‍♂️ Любой формат (Аудио или Видео)</option>
                <option value="audio">🎤 Только Аудио/Голосовое</option>
                <option value="video">📹 Только Видео/Кружок</option>
              </select>
            </div>
          ))}

          <div className="btn-row">
            <button
              type="button"
              className="btn btn-secondary"
              style={{ flex: 1 }}
              onClick={() => setTaskBlocks((p) => [...p, emptyTask()])}
            >
              <Plus size={15} /> Ещё задание
            </button>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={saving}>
              <Send size={15} /> {saving ? "..." : "Опубликовать"}
            </button>
          </div>
        </form>
      </Modal>
    </>
  );
}
