import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";

import { apiFetch } from "../api/client";
import EmptyState from "../components/EmptyState";

export default function StudentSubmissionsPage({ notify }) {
  const [subs, setSubs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/student/submissions")
      .then((d) => setSubs(d.submissions || []))
      .catch((e) => notify("❌ " + e.message))
      .finally(() => setLoading(false));
  }, [notify]);

  if (loading) {
    return (
      <div className="loader-wrap">
        <div className="spinner" />
      </div>
    );
  }

  if (!subs.length) {
    return (
      <EmptyState
        icon="📝"
        title="Пока нет выполненных заданий"
        subtitle="Выберите тему на вкладке «Темы» и запишите свой первый ответ в боте."
      />
    );
  }

  return (
    <>
      <div className="section-title">✅ История сдач</div>
      {subs.map((s, idx) => (
        <motion.div
          key={s.id}
          className="card"
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.03 }}
        >
          <div className="card-row">
            <div>
              <div className="muted" style={{ fontSize: 12 }}>
                {s.topic}
              </div>
              <div className="card-title">{s.title}</div>
            </div>
            {s.grade ? (
              <span className="badge badge-success">⭐️ {s.grade} / 5</span>
            ) : (
              <span className="badge badge-warning">⏳ На проверке</span>
            )}
          </div>
          <p className="muted">{s.description}</p>
          {s.teacher_comment && (
            <div className="sub-item" style={{ fontSize: 13 }}>
              <b>👨‍🏫 Комментарий:</b> {s.teacher_comment}
            </div>
          )}
        </motion.div>
      ))}
    </>
  );
}
