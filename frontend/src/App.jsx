import React, { useCallback, useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  BarChart3,
  BookOpen,
  CheckCircle2,
  ClipboardCheck,
  FilePlus2,
  Shield,
  User as UserIcon,
  Users,
} from "lucide-react";

import { apiFetch, tg } from "./api/client";
import BottomNav from "./components/BottomNav";
import EmptyState from "./components/EmptyState";
import Header from "./components/Header";
import Toast from "./components/Toast";
import AdminPage from "./pages/AdminPage";
import ProfilePage from "./pages/ProfilePage";
import StudentSubmissionsPage from "./pages/StudentSubmissionsPage";
import StudentTopicsPage from "./pages/StudentTopicsPage";
import TeacherCheckPage from "./pages/TeacherCheckPage";
import TeacherGroupsPage from "./pages/TeacherGroupsPage";
import TeacherStatsPage from "./pages/TeacherStatsPage";
import TeacherTopicsPage from "./pages/TeacherTopicsPage";

export default function App() {
  const [user, setUser] = useState(null);
  const [botUsername, setBotUsername] = useState("");
  const [activeTab, setActiveTab] = useState("");
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState("");

  const notify = useCallback((msg) => {
    setToast(msg);
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => setToast(""), 2800);
  }, []);

  const refreshMe = useCallback(async () => {
    const data = await apiFetch("/api/me");
    setUser(data.user);
    setBotUsername(data.bot_username || "");
    return data.user;
  }, []);

  useEffect(() => {
    if (tg) {
      tg.ready();
      tg.expand();
    }
    refreshMe()
      .then((u) => {
        setActiveTab(u.role === "student" ? "student_topics" : "teacher_groups");
      })
      .catch((err) => setAuthError(err.message))
      .finally(() => setLoading(false));
  }, [refreshMe]);

  const tabs = useMemo(() => {
    if (!user) return [];
    if (user.role === "student") {
      return [
        { id: "student_topics", icon: BookOpen, label: "Темы" },
        { id: "student_subs", icon: CheckCircle2, label: "Сдачи" },
        { id: "profile", icon: UserIcon, label: "Профиль" },
      ];
    }
    const base = [
      { id: "teacher_groups", icon: Users, label: "Классы" },
      { id: "teacher_topics", icon: FilePlus2, label: "Задания" },
      { id: "teacher_check", icon: ClipboardCheck, label: "Проверка" },
      { id: "teacher_stats", icon: BarChart3, label: "Статистика" },
      { id: "profile", icon: UserIcon, label: "Профиль" },
    ];
    if (user.role === "admin" || user.role === "founder") {
      base.push({ id: "admin", icon: Shield, label: "Админ" });
    }
    return base;
  }, [user]);

  return (
    <div className="app-shell">
      <Header user={user} />

      <main className="content">
        {loading ? (
          <div className="loader-wrap">
            <div className="spinner" />
            <p className="muted">Загружаем данные...</p>
          </div>
        ) : authError ? (
          <EmptyState icon="🔒" title="Нет доступа" subtitle={authError} />
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              style={{ display: "flex", flexDirection: "column", gap: 14 }}
            >
              {activeTab === "profile" && (
                <ProfilePage user={user} onUpdated={refreshMe} notify={notify} />
              )}
              {activeTab === "student_topics" && (
                <StudentTopicsPage botUsername={botUsername} notify={notify} />
              )}
              {activeTab === "student_subs" && (
                <StudentSubmissionsPage notify={notify} />
              )}
              {activeTab === "teacher_groups" && (
                <TeacherGroupsPage notify={notify} />
              )}
              {activeTab === "teacher_topics" && (
                <TeacherTopicsPage notify={notify} />
              )}
              {activeTab === "teacher_check" && (
                <TeacherCheckPage botUsername={botUsername} notify={notify} />
              )}
              {activeTab === "teacher_stats" && (
                <TeacherStatsPage notify={notify} />
              )}
              {activeTab === "admin" && (
                <AdminPage currentUser={user} notify={notify} />
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </main>

      {user && !authError && (
        <BottomNav tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      )}
      <Toast message={toast} />
    </div>
  );
}
