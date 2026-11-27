import React, { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Headphones, Star } from "lucide-react";

import { apiFetch, openBotDeepLink } from "../api/client";
import EmptyState from "../components/EmptyState";
import Modal from "../components/Modal";

export default function TeacherCheckPage({ botUsername, notify }) {
  const [filter, setFilter] = useState("pending");
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);

  const [gradingSub, setGradingSub] = useState(null);
  const [grade, setGrade] = useState(5);
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);

  const loadSubs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch(`/api/teacher/submissions?status_filter=${filter}`);
      setSubs(data.submissions || []);
    } catch (e) {
      notify("❌ " + e.message);
    } finally {
      setLoading(false);
    }
  }, [filter, notify]);

  useEffect(() => {
    loadSubs();
  }, [loadSubs]);

  const handleSaveGrade = async (e) => {
    e.preventDefault();
    if (!gradingSub) return;
    setSaving(true);
    try {
      await apiFetch(`/api/teacher/submissions/${gradingSub.id}/grade`, {
        method: "POST",
        body: JSON.stringify({ grade, comment }),
      });
      setGradingSub(null);
      notify("✅ Оценка сохранена");
      await loadSubs();
    } catch (err) {
      notify("❌ " + err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="section-title">✅ Проверка ответов</div>

      <div className="pills">
        <button
          type="button"
          className={`pill ${filter === "pending" ? "active" : ""}`}
          onClick={() => setFilter("pending")}
        >
          ⏳ На проверке
        </button>
        <button
          type="button"
          className={`pill ${filter === "graded" ? "active" : ""}`}
          onClick={() => setFilter("graded")}
        >
          ✅ Проверенные
        </button>
      </div>

      {loading ? (
        <div className="loader-wrap">
          <div className="spinner" />
        </div>
      ) : !subs.length ? (
        <EmptyState
          icon="🎉"
          subtitle={filter === "pending" ? "Все ответы проверены!" : "Проверенных работ пока нет"}
        />
      ) : (
        subs.map((s, idx) => (
          <motion.div
            key={s.id}
            className="card"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03 }}
          >
            <div className="card-row">
              <div>
                <div className="card-title">👤 {s.student_name}</div>
                <div className="muted">
                  {s.class_name} - {s.group_name} · {s.topic} | {s.title}
                </div>
              </div>
              {s.grade ? (
                <span className="badge badge-success">⭐️ {s.grade}</span>
              ) : (
                <span className="badge badge-warning">⏳ Ждёт</span>
              )}
            </div>

            {s.teacher_comment && (
              <div className="sub-item muted">Комментарий: {s.teacher_comment}</div>
            )}

            <div className="btn-row">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ flex: 1 }}
                onClick={() =>
                  openBotDeepLink(botUsername, `review_${s.id}`, () =>
                    notify("Укажите BOT_USERNAME в .env для прослушивания в чате.")
                  )
                }
              >
                <Headphones size={14} /> Прослушать в боте
              </button>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                style={{ flex: 1 }}
                onClick={() => {
                  setGradingSub(s);
                  setGrade(s.grade || 5);
                  setComment(s.teacher_comment || "");
                }}
              >
                <Star size={14} /> {s.grade ? "Изменить" : "Оценить"}
              </button>
            </div>
          </motion.div>
        ))
      )}

      <Modal open={Boolean(gradingSub)} title="Оценка работы" onClose={() => setGradingSub(null)}>
        <form onSubmit={handleSaveGrade} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div className="field">
            <label>Оценка (1–5)</label>
            <div className="grade-picker">
              {[1, 2, 3, 4, 5].map((g) => (
                <button
                  key={g}
                  type="button"
                  className={`grade-btn ${grade === g ? "selected" : ""}`}
                  onClick={() => setGrade(g)}
                >
                  {g}
                </button>
              ))}
            </div>
          </div>
          <div className="field">
            <label>Комментарий ученику</label>
            <textarea
              className="textarea"
              placeholder="Отличное произношение!"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>
          <button type="submit" className="btn btn-primary btn-block" disabled={saving}>
            {saving ? "Сохраняем..." : "Сохранить оценку"}
          </button>
        </form>
      </Modal>
    </>
  );
}
