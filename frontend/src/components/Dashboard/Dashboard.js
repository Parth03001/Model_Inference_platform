import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import StatsCard from '../StatsCard/StatsCard';
import { getStats, listCameras, listModels } from '../../services/api';
import './Dashboard.css';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit: { opacity: 0, y: -16, transition: { duration: 0.25 } },
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [cameras, setCameras] = useState([]);
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, camRes, modRes] = await Promise.all([
        getStats(),
        listCameras(),
        listModels(),
      ]);
      setStats(statsRes.data);
      setCameras(camRes.data.slice(0, 4));
      setModels(modRes.data.slice(0, 4));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 10000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return (
    <motion.div className="dashboard" variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <div className="dashboard__header">
        <div>
          <h1 className="dashboard__title">Dashboard</h1>
          <p className="dashboard__subtitle">Overview of your inference platform</p>
        </div>
        <button className="btn-refresh" onClick={fetchAll}>↺ Refresh</button>
      </div>

      {/* Stats Grid */}
      <div className="dashboard__stats">
        <StatsCard
          icon="◈"
          label="Total Detections"
          value={stats?.total_detections ?? 0}
          color="primary"
          loading={loading}
        />
        <StatsCard
          icon="◎"
          label="Total Cameras"
          value={stats?.total_cameras ?? 0}
          color="info"
          loading={loading}
        />
        <StatsCard
          icon="⬡"
          label="Models Uploaded"
          value={stats?.total_models ?? 0}
          color="success"
          loading={loading}
        />
        <StatsCard
          icon="▶"
          label="Active Streams"
          value={stats?.active_streams ?? 0}
          color="warning"
          loading={loading}
        />
      </div>

      <div className="dashboard__grid">
        {/* Cameras Overview */}
        <motion.div
          className="dashboard__panel"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.1 }}
        >
          <div className="panel__header">
            <h2 className="panel__title">Cameras</h2>
            <button className="panel__action" onClick={() => navigate('/cameras')}>
              View all →
            </button>
          </div>
          {cameras.length === 0 && !loading ? (
            <div className="panel__empty">
              <p>No cameras added yet.</p>
              <button className="btn-inline" onClick={() => navigate('/cameras')}>Add Camera</button>
            </div>
          ) : (
            <ul className="panel__list">
              {cameras.map((cam) => (
                <li key={cam.id} className="panel__item">
                  <div className="item__icon">◎</div>
                  <div className="item__info">
                    <span className="item__name">{cam.name}</span>
                    <span className="item__sub">{cam.rtsp_url.replace(/:[^:@]+@/, ':***@')}</span>
                  </div>
                  <span className={`status-badge ${cam.is_streaming ? 'status-badge--live' : 'status-badge--idle'}`}>
                    {cam.is_streaming ? 'LIVE' : 'IDLE'}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </motion.div>

        {/* Models Overview */}
        <motion.div
          className="dashboard__panel"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.15 }}
        >
          <div className="panel__header">
            <h2 className="panel__title">Models</h2>
            <button className="panel__action" onClick={() => navigate('/models')}>
              View all →
            </button>
          </div>
          {models.length === 0 && !loading ? (
            <div className="panel__empty">
              <p>No models uploaded yet.</p>
              <button className="btn-inline" onClick={() => navigate('/models')}>Upload Model</button>
            </div>
          ) : (
            <ul className="panel__list">
              {models.map((m) => (
                <li key={m.id} className="panel__item">
                  <div className="item__icon">⬡</div>
                  <div className="item__info">
                    <span className="item__name">{m.name}</span>
                    <span className="item__sub">{m.filename}</span>
                  </div>
                  {m.is_active && (
                    <span className="status-badge status-badge--active">ACTIVE</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </motion.div>

        {/* Label Distribution */}
        {stats?.label_distribution?.length > 0 && (
          <motion.div
            className="dashboard__panel dashboard__panel--full"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="panel__header">
              <h2 className="panel__title">Detection Labels</h2>
              <button className="panel__action" onClick={() => navigate('/detections')}>
                View history →
              </button>
            </div>
            <div className="label-bars">
              {stats.label_distribution.map((item) => {
                const max = Math.max(...stats.label_distribution.map((d) => d.count));
                const pct = Math.round((item.count / max) * 100);
                return (
                  <div key={item.label} className="label-bar-row">
                    <span className="label-bar-name">{item.label}</span>
                    <div className="label-bar-track">
                      <motion.div
                        className="label-bar-fill"
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8, delay: 0.3 }}
                      />
                    </div>
                    <span className="label-bar-count">{item.count}</span>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </div>

      {/* Quick actions */}
      <motion.div
        className="dashboard__quick-actions"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <h2 className="dashboard__section-title">Quick Actions</h2>
        <div className="quick-actions-grid">
          {[
            { icon: '⬡', label: 'Upload Model', path: '/models', color: 'success' },
            { icon: '◎', label: 'Add Camera', path: '/cameras', color: 'info' },
            { icon: '▶', label: 'Start Stream', path: '/stream', color: 'warning' },
            { icon: '◈', label: 'View Detections', path: '/detections', color: 'primary' },
          ].map((a) => (
            <motion.button
              key={a.path}
              className={`quick-action quick-action--${a.color}`}
              onClick={() => navigate(a.path)}
              whileHover={{ scale: 1.04, y: -4 }}
              whileTap={{ scale: 0.97 }}
            >
              <span className="quick-action__icon">{a.icon}</span>
              <span className="quick-action__label">{a.label}</span>
            </motion.button>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
}
