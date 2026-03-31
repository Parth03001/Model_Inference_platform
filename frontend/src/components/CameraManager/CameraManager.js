import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { addCamera, listCameras, deleteCamera, updateCamera } from '../../services/api';
import './CameraManager.css';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit: { opacity: 0, y: -16 },
};

export default function CameraManager() {
  const [cameras, setCameras] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState({ name: '', rtsp_url: '' });

  const fetchCameras = useCallback(async () => {
    try {
      const res = await listCameras();
      setCameras(res.data);
    } catch {
      setError('Failed to load cameras.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCameras(); }, [fetchCameras]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || !form.rtsp_url.trim()) {
      setError('Name and RTSP URL are required.');
      return;
    }
    setSubmitting(true);
    setError('');
    try {
      if (editId) {
        await updateCamera(editId, form);
        setSuccess('Camera updated.');
        setEditId(null);
      } else {
        await addCamera(form);
        setSuccess('Camera added successfully!');
      }
      setForm({ name: '', rtsp_url: '' });
      fetchCameras();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save camera.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (cam) => {
    setEditId(cam.id);
    setForm({ name: cam.name, rtsp_url: cam.rtsp_url });
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete camera "${name}"?`)) return;
    try {
      await deleteCamera(id);
      setCameras((c) => c.filter((x) => x.id !== id));
    } catch {
      setError('Failed to delete camera.');
    }
  };

  const maskUrl = (url) => url.replace(/:[^:@]+@/, ':***@');

  return (
    <motion.div className="camera-manager" variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <div className="page-header">
        <h1 className="page-title">Camera Management</h1>
        <p className="page-subtitle">Add and manage your RTSP camera streams</p>
      </div>

      {/* Add/Edit Form */}
      <motion.div
        className="camera-form-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <h2 className="camera-form-card__title">
          {editId ? '✏ Edit Camera' : '+ Add Camera'}
        </h2>
        <form onSubmit={handleSubmit} className="camera-form">
          <div className="camera-form__row">
            <div className="form-field">
              <label className="form-label">Camera Name</label>
              <input
                className="form-input"
                type="text"
                placeholder="e.g. Main Entrance CCTV"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="form-field camera-form__url-field">
              <label className="form-label">RTSP URL</label>
              <input
                className="form-input"
                type="text"
                placeholder="rtsp://user:pass@192.168.1.1/streaming/channels/101"
                value={form.rtsp_url}
                onChange={(e) => setForm({ ...form, rtsp_url: e.target.value })}
              />
            </div>
          </div>

          <AnimatePresence>
            {error && (
              <motion.p
                className="form-error"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                {error}
              </motion.p>
            )}
            {success && (
              <motion.p
                className="form-success"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                {success}
              </motion.p>
            )}
          </AnimatePresence>

          <div className="camera-form__actions">
            <motion.button
              type="submit"
              className="btn-submit"
              disabled={submitting}
              whileHover={{ scale: submitting ? 1 : 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              {submitting ? (
                <span className="btn-spinner" />
              ) : editId ? (
                'Update Camera'
              ) : (
                '+ Add Camera'
              )}
            </motion.button>
            {editId && (
              <button
                type="button"
                className="btn-cancel"
                onClick={() => { setEditId(null); setForm({ name: '', rtsp_url: '' }); }}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </motion.div>

      {/* Cameras List */}
      <div className="cameras-section">
        <div className="cameras-section__header">
          <h2 className="section-title">Cameras ({cameras.length})</h2>
        </div>

        {loading ? (
          <div className="cameras-loading">
            {[1, 2, 3].map((i) => <div key={i} className="camera-skeleton" />)}
          </div>
        ) : cameras.length === 0 ? (
          <div className="cameras-empty">
            <span className="cameras-empty__icon">◎</span>
            <p>No cameras added yet. Add your first camera above.</p>
          </div>
        ) : (
          <div className="cameras-grid">
            <AnimatePresence>
              {cameras.map((cam, i) => (
                <motion.div
                  key={cam.id}
                  className={`camera-card ${cam.is_streaming ? 'camera-card--live' : ''}`}
                  layout
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: i * 0.05 } }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  whileHover={{ y: -4 }}
                >
                  <div className="camera-card__top">
                    <div className="camera-card__icon-wrap">
                      <span className="camera-card__icon">◎</span>
                      {cam.is_streaming && <span className="camera-card__live-dot" />}
                    </div>
                    <div className="camera-card__info">
                      <div className="camera-card__name">{cam.name}</div>
                      <div className="camera-card__url" title={cam.rtsp_url}>
                        {maskUrl(cam.rtsp_url)}
                      </div>
                    </div>
                    <span className={`camera-status ${cam.is_streaming ? 'camera-status--live' : 'camera-status--idle'}`}>
                      {cam.is_streaming ? '● LIVE' : '○ IDLE'}
                    </span>
                  </div>
                  <div className="camera-card__meta">
                    <span>Added {new Date(cam.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="camera-card__actions">
                    <button className="cam-btn cam-btn--edit" onClick={() => handleEdit(cam)}>
                      Edit
                    </button>
                    <button className="cam-btn cam-btn--delete" onClick={() => handleDelete(cam.id, cam.name)}>
                      Delete
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </motion.div>
  );
}
