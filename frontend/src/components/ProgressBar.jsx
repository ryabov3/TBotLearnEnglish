import React from "react";
import { motion } from "framer-motion";

export default function ProgressBar({ value }) {
  const pct = Math.max(0, Math.min(100, Math.round(value || 0)));
  return (
    <div className="progress-track">
      <motion.div
        className="progress-fill"
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.45, ease: "easeOut" }}
      />
    </div>
  );
}
