import React from "react";
import { motion } from "framer-motion";

export default function BottomNav({ tabs, activeTab, onChange }) {
  return (
    <nav className="bottom-nav">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const active = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            className={`nav-item ${active ? "active" : ""}`}
            onClick={() => onChange(tab.id)}
          >
            {active && (
              <motion.span
                layoutId="activeNavPill"
                className="nav-pill"
                transition={{ type: "spring", stiffness: 420, damping: 32 }}
              />
            )}
            <Icon size={19} />
            <span>{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}
