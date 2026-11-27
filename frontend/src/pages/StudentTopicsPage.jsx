import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Mic, CheckCircle2, Circle } from "lucide-react";

import { apiFetch, openBotDeepLink } from "../api/client";
import EmptyState from "../components/EmptyState";
import ProgressBar from "../components/ProgressBar";

const FORMAT_LABELS = {
  audio: "🎤 Только аудио",
  video: "📹 Только видео",
  any: "🎙 Аудио или видео",
};

export default function StudentTopicsPage({ botUsername, notify }) {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState("new");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch("/api/student/topics")
      .then(setData)
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

  if (!data || !data.has_group) {
    return (
      <EmptyState
        icon="🏫"
        title="Вы ещё не добавлены в группу"
        subtitle="Попросите учителя добавить ваш @username в класс — после этого здесь появятся темы и задания."
      />
    );
  }

  const lists = {
    new: data.new_topics,
    progress: data.in_progress,
    done: data.completed_topics,
  };
  const current = lists[filter] || [];

  return (
    <>
      <div className="section-header">
        <div className="section-title">📚 Мои темы</div>
        <span className="badge badge-accent">
          {data.class_name} · {data.group_name}
        </span>
      </div>

      <div className="pills">
        <button
          type="button"
          className={`pill ${filter === "new" ? "active" : ""}`}
          onClick={() => setFilter("new")}
        >
          🆕 Новые ({data.new_topics.length})
        </button>
        <button
          type="button"
          className={`pill ${filter === "progress" ? "active" : ""}`}
          onClick={() => setFilter("progress")}
        >
          ⏳ В процессе ({data.in_progress.length})
        </button>
        <button
          type="button"
          className={`pill ${filter === "done" ? "active" : ""}`}
          onClick={() => setFilter("done")}
        >
          ✅ Завершённые ({data.completed_topics.length})
        </button>
      </div>

      {!current.length ? (
        <EmptyState icon="🎉" subtitle="В этом разделе пока пусто" />
      ) : (
        current.map((topic, idx) => {
          const pct = Math.round((topic.completed / Math.max(1, topic.total)) * 100);
          return (
            <motion.div
              key={topic.topic}
              className="card"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.04 }}
            >
              <div className="card-row">
                <div className="card-title">📂 {topic.topic}</div>
                <span className={`badge ${pct === 100 ? "badge-success" : "badge-accent"}`}>
                  {topic.completed}/{topic.total}
                </span>
              </div>
              <ProgressBar value={pct} />
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 4 }}>
                {topic.tasks.map((t) => (
                  <div key={t.id} className="sub-item card-row">
                    <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                      {t.completed ? (
                        <CheckCircle2 size={16} color="#10b981" style={{ marginTop: 2, flexShrink: 0 }} />
                      ) : (
                        <Circle size={16} color="#94a3b8" style={{ marginTop: 2, flexShrink: 0 }} />
                      )}
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 600 }}>{t.title}</div>
                        <div className="muted" style={{ fontSize: 12 }}>
                          {FORMAT_LABELS[t.expected_answer] || t.expected_answer}
                        </div>
                      </div>
                    </div>
                    {!t.completed ? (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        onClick={() =>
                          openBotDeepLink(botUsername, `task_${t.id}`, () =>
                            notify("Укажите BOT_USERNAME в .env для быстрого перехода в чат.")
                          )
                        }
                      >
                        <Mic size={14} /> Сдать
                      </button>
                    ) : (
                      <span className="badge badge-success">Сдано</span>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          );
        })
      )}
    </>
  );
}
