import React from "react";
import { GraduationCap } from "lucide-react";

const ROLE_LABELS = {
  student: "Ученик",
  teacher: "Учитель",
  admin: "Админ",
  founder: "Основатель",
};

export default function Header({ user }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-icon">
          <GraduationCap size={22} />
        </div>
        <div>
          <div className="brand-title">LearnEnglish</div>
          <div className="brand-subtitle">
            {user ? `${user.first_name || ""} ${user.last_name || ""}`.trim() : "Загрузка..."}
          </div>
        </div>
      </div>
      {user && (
        <span className={`role-badge ${user.role}`}>
          {ROLE_LABELS[user.role] || user.role}
        </span>
      )}
    </header>
  );
}
