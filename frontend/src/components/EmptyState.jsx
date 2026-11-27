import React from "react";

export default function EmptyState({ icon, title, subtitle }) {
  return (
    <div className="card empty-state">
      <div style={{ fontSize: 36 }}>{icon}</div>
      {title && <div className="card-title">{title}</div>}
      {subtitle && <p className="muted">{subtitle}</p>}
    </div>
  );
}
