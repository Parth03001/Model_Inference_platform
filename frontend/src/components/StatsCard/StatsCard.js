import React from 'react';
import { motion } from 'framer-motion';
import './StatsCard.css';

export default function StatsCard({ icon, label, value, color = 'primary', loading = false }) {
  return (
    <motion.div
      className={`stats-card stats-card--${color}`}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      whileHover={{ y: -4, borderColor: 'var(--border-glow)' }}
    >
      <div className="stats-card__icon">{icon}</div>
      <div className="stats-card__body">
        <div className="stats-card__value">
          {loading ? <span className="stats-card__skeleton" /> : value}
        </div>
        <div className="stats-card__label">{label}</div>
      </div>
    </motion.div>
  );
}
