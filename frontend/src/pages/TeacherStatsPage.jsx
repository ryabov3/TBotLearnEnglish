import React, { useEffect, useState } from "react";

import { apiFetch } from "../api/client";
import EmptyState from "../components/EmptyState";
import ProgressBar from "../components/ProgressBar";

export default function TeacherStatsPage({ notify }) {
  const [groups, setGroups] = useState([]);
  const [activeGroupId, setActiveGroupId] = useState(null);
  const [stats, setStats] = useState(null);
  const [loadingGroups, setLoadingGroups] = useState(true);
  const [loadingStats, setLoadingStats] = useState(false);

  useEffect(() => {
    apiFetch("/api/teacher/groups")
      .then((d) => {
        const list = d.groups || [];
        setGroups(list);
        if (list.length) setActiveGroupId(list[0].id);
      })
      .catch((e) => notify("❌ " + e.message))
      .finally(() => setLoadingGroups(false));
  }, [notify]);

  useEffect(() => {
    if (!activeGroupId) return;
    setLoadingStats(true);
    apiFetch(`/api/teacher/groups/${activeGroupId}/stats`)
      .then(setStats)
      .catch((e) => notify("❌ " + e.message))
      .finally(() => setLoadingStats(false));
  }, [activeGroupId, notify]);

  if (loadingGroups) {
    return (
      <div className="loader-wrap">
        <div className="spinner" />
      </div>
    );
  }

  if (!groups.length) {
    return <EmptyState icon="📊" subtitle="Сначала создайте группу" />;
  }

  return (
    <>
      <div className="section-title">📊 Статистика по группам</div>

      <div className="pills">
        {groups.map((g) => (
          <button
            key={g.id}
            type="button"
            className={`pill ${activeGroupId === g.id ? "active" : ""}`}
            onClick={() => setActiveGroupId(g.id)}
          >
            {g.class_name} - {g.group_name}
          </button>
        ))}
      </div>

      {loadingStats || !stats ? (
        <div className="loader-wrap">
          <div className="spinner" />
        </div>
      ) : (
        <>
          <div className="kpi-grid cols-2">
            <div className="kpi-card">
              <div className="kpi-value">
                {stats.overall_avg !== null ? `⭐️ ${stats.overall_avg}` : "—"}
              </div>
              <div className="kpi-label">Общий средний балл</div>
            </div>
            <div className="kpi-card">
              <div className="kpi-value">{stats.students.length}</div>
              <div className="kpi-label">Учеников в группе</div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">📝 Средний балл по заданиям</div>
            {stats.tasks.length ? (
              stats.tasks.map((t) => (
                <div key={t.id}>
                  <div className="card-row" style={{ marginBottom: 4 }}>
                    <span style={{ fontSize: 13 }}>
                      {t.topic} · {t.title}
                    </span>
                    <strong style={{ fontSize: 13 }}>{t.avg !== null ? t.avg : "—"}</strong>
                  </div>
                  <ProgressBar value={t.avg ? (t.avg / 5) * 100 : 0} />
                </div>
              ))
            ) : (
              <div className="muted">Заданий пока нет</div>
            )}
          </div>

          <div className="card">
            <div className="card-title">👥 Успеваемость учеников</div>
            {stats.students.length ? (
              stats.students.map((s) => (
                <div key={s.id} className="sub-item card-row">
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{s.name}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      🔥 {s.current_streak} дн. · ✅ {s.total_completed} сдач
                    </div>
                  </div>
                  <span className={`badge ${s.avg >= 4 ? "badge-success" : "badge-accent"}`}>
                    {s.avg !== null ? `⭐️ ${s.avg}` : "Нет оценок"}
                  </span>
                </div>
              ))
            ) : (
              <div className="muted">Учеников пока нет</div>
            )}
          </div>
        </>
      )}
    </>
  );
}
