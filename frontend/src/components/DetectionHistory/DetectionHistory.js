import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { listDetections, listCameras } from '../../services/api';
import './DetectionHistory.css';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit: { opacity: 0, y: -16 },
};

function ConfidenceBadge({ value }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? 'high' : pct >= 50 ? 'mid' : 'low';
  return <span className={`conf-badge conf-badge--${color}`}>{pct}%</span>;
}

function DetectionModal({ detection, onClose }) {
  if (!detection) return null;
  return (
    <motion.div
      className="modal-backdrop"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className="modal"
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal__header">
          <h3 className="modal__title">{detection.label}</h3>
          <button className="modal__close" onClick={onClose}>✕</button>
        </div>
        {detection.image_base64 && (
          <img
            className="modal__image"
            src={`data:image/jpeg;base64,${detection.image_base64}`}
            alt="Detection snapshot"
          />
        )}
        <div className="modal__meta">
          <div className="modal__row">
            <span className="modal__key">Camera</span>
            <span className="modal__val">{detection.camera_name || detection.camera_id}</span>
          </div>
          <div className="modal__row">
            <span className="modal__key">Model</span>
            <span className="modal__val">{detection.model_name || detection.model_id}</span>
          </div>
          <div className="modal__row">
            <span className="modal__key">Confidence</span>
            <span className="modal__val">{Math.round(detection.confidence * 100)}%</span>
          </div>
          <div className="modal__row">
            <span className="modal__key">Timestamp</span>
            <span className="modal__val">{new Date(detection.timestamp).toLocaleString()}</span>
          </div>
          {detection.bbox_x1 != null && (
            <div className="modal__row">
              <span className="modal__key">BBox</span>
              <span className="modal__val">
                [{Math.round(detection.bbox_x1)}, {Math.round(detection.bbox_y1)},&nbsp;
                {Math.round(detection.bbox_x2)}, {Math.round(detection.bbox_y2)}]
              </span>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

export default function DetectionHistory() {
  const [detections, setDetections] = useState([]);
  const [cameras, setCameras] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ camera_id: '', label: '' });
  const [selected, setSelected] = useState(null);
  const PER_PAGE = 20;

  const fetchDetections = useCallback(async () => {
    setLoading(true);
    try {
      const params = { page, per_page: PER_PAGE };
      if (filters.camera_id) params.camera_id = filters.camera_id;
      if (filters.label) params.label = filters.label;
      const res = await listDetections(params);
      setDetections(res.data.data);
      setTotal(res.data.total);
      setTotalPages(res.data.total_pages);
    } catch {
      setDetections([]);
    } finally {
      setLoading(false);
    }
  }, [page, filters]);

  useEffect(() => {
    listCameras().then((r) => setCameras(r.data)).catch(() => {});
  }, []);

  useEffect(() => { fetchDetections(); }, [fetchDetections]);

  const handleFilter = (key, value) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };

  return (
    <motion.div className="detection-history" variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <div className="page-header">
        <div>
          <h1 className="page-title">Detection History</h1>
          <p className="page-subtitle">{total} total detections stored</p>
        </div>
        <button className="btn-refresh" onClick={fetchDetections}>↺ Refresh</button>
      </div>

      {/* Filters */}
      <motion.div
        className="filters-bar"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <div className="form-field">
          <label className="form-label">Camera</label>
          <select
            className="form-select"
            value={filters.camera_id}
            onChange={(e) => handleFilter('camera_id', e.target.value)}
          >
            <option value="">All cameras</option>
            {cameras.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label className="form-label">Label</label>
          <input
            className="form-input"
            type="text"
            placeholder="Filter by label..."
            value={filters.label}
            onChange={(e) => handleFilter('label', e.target.value)}
          />
        </div>
      </motion.div>

      {/* Table */}
      <motion.div
        className="detections-table-wrap"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.15 }}
      >
        <table className="detections-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Camera</th>
              <th>Label</th>
              <th>Confidence</th>
              <th>Model</th>
              <th>Snapshot</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="table-skeleton-row">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j}><div className="table-skeleton-cell" /></td>
                  ))}
                </tr>
              ))
            ) : detections.length === 0 ? (
              <tr>
                <td colSpan={6} className="table-empty">No detections found.</td>
              </tr>
            ) : (
              detections.map((d) => (
                <motion.tr
                  key={d.id}
                  className="table-row"
                  whileHover={{ backgroundColor: 'rgba(99,102,241,0.04)' }}
                  onClick={() => setSelected(d)}
                >
                  <td className="td-timestamp">
                    {new Date(d.timestamp).toLocaleString()}
                  </td>
                  <td className="td-camera">{d.camera_name || `#${d.camera_id}`}</td>
                  <td className="td-label">
                    <span className="label-chip">{d.label}</span>
                  </td>
                  <td><ConfidenceBadge value={d.confidence} /></td>
                  <td className="td-model">{d.model_name || `#${d.model_id}`}</td>
                  <td>
                    {d.image_base64 ? (
                      <img
                        className="table-thumb"
                        src={`data:image/jpeg;base64,${d.image_base64}`}
                        alt="snapshot"
                      />
                    ) : (
                      <span className="td-no-img">—</span>
                    )}
                  </td>
                </motion.tr>
              ))
            )}
          </tbody>
        </table>
      </motion.div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          <button
            className="page-btn"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
          >
            ‹ Prev
          </button>
          <span className="page-info">
            Page {page} of {totalPages}
          </span>
          <button
            className="page-btn"
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
          >
            Next ›
          </button>
        </div>
      )}

      {/* Modal */}
      <AnimatePresence>
        {selected && (
          <DetectionModal detection={selected} onClose={() => setSelected(null)} />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
