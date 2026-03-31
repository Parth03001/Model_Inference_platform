import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadModel, listModels, deleteModel, activateModel } from '../../services/api';
import './ModelUpload.css';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit: { opacity: 0, y: -16 },
};

export default function ModelUpload() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [modelName, setModelName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  const fetchModels = useCallback(async () => {
    try {
      const res = await listModels();
      setModels(res.data);
    } catch {
      setError('Failed to load models.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchModels(); }, [fetchModels]);

  const handleFile = (file) => {
    if (!file) return;
    if (!file.name.match(/\.(pt|engine|onnx)$/i)) {
      setError('Only .pt, .engine, or .onnx files are allowed.');
      return;
    }
    setSelectedFile(file);
    setError('');
    if (!modelName) setModelName(file.name.replace(/\.[^.]+$/, ''));
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  }, [modelName]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile || !modelName.trim()) {
      setError('Please provide a model name and select a file.');
      return;
    }
    const formData = new FormData();
    formData.append('name', modelName.trim());
    formData.append('file', selectedFile);

    setUploading(true);
    setUploadProgress(0);
    setError('');
    try {
      await uploadModel(formData);
      setSuccess(`Model "${modelName}" uploaded successfully!`);
      setModelName('');
      setSelectedFile(null);
      fetchModels();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete model "${name}"?`)) return;
    try {
      await deleteModel(id);
      setModels((m) => m.filter((x) => x.id !== id));
    } catch {
      setError('Failed to delete model.');
    }
  };

  const handleActivate = async (id) => {
    try {
      await activateModel(id);
      fetchModels();
    } catch {
      setError('Failed to activate model.');
    }
  };

  return (
    <motion.div className="model-upload" variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <div className="page-header">
        <h1 className="page-title">Model Weights</h1>
        <p className="page-subtitle">Upload and manage your YOLO model weight files</p>
      </div>

      {/* Upload Form */}
      <motion.div
        className="upload-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <h2 className="upload-card__title">Upload New Model</h2>
        <form onSubmit={handleSubmit} className="upload-form">
          <div className="form-field">
            <label className="form-label">Model Name</label>
            <input
              className="form-input"
              type="text"
              placeholder="e.g. Helmet Detector v2"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            />
          </div>

          <div
            className={`dropzone ${dragging ? 'dropzone--active' : ''} ${selectedFile ? 'dropzone--has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pt,.engine,.onnx"
              style={{ display: 'none' }}
              onChange={(e) => handleFile(e.target.files[0])}
            />
            <AnimatePresence mode="wait">
              {selectedFile ? (
                <motion.div
                  key="file"
                  className="dropzone__file-info"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <span className="dropzone__file-icon">⬡</span>
                  <span className="dropzone__file-name">{selectedFile.name}</span>
                  <span className="dropzone__file-size">
                    {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB
                  </span>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  className="dropzone__placeholder"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <span className="dropzone__icon">⬆</span>
                  <span className="dropzone__text">Drop your weight file here</span>
                  <span className="dropzone__hint">.pt · .engine · .onnx</span>
                </motion.div>
              )}
            </AnimatePresence>
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

          <motion.button
            className="btn-submit"
            type="submit"
            disabled={uploading}
            whileHover={{ scale: uploading ? 1 : 1.02 }}
            whileTap={{ scale: uploading ? 1 : 0.98 }}
          >
            {uploading ? (
              <span className="btn-submit__spinner" />
            ) : (
              '⬆ Upload Model'
            )}
          </motion.button>
        </form>
      </motion.div>

      {/* Models List */}
      <div className="models-section">
        <h2 className="section-title">Uploaded Models</h2>
        {loading ? (
          <div className="models-loading">
            {[1, 2, 3].map((i) => (
              <div key={i} className="model-skeleton" />
            ))}
          </div>
        ) : models.length === 0 ? (
          <div className="models-empty">
            <span className="models-empty__icon">⬡</span>
            <p>No models uploaded yet. Upload your first model above.</p>
          </div>
        ) : (
          <motion.div className="models-grid" layout>
            <AnimatePresence>
              {models.map((m) => (
                <motion.div
                  key={m.id}
                  className={`model-card ${m.is_active ? 'model-card--active' : ''}`}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  whileHover={{ y: -4 }}
                >
                  <div className="model-card__icon">⬡</div>
                  <div className="model-card__info">
                    <div className="model-card__name">{m.name}</div>
                    <div className="model-card__file">{m.filename}</div>
                    <div className="model-card__date">
                      Uploaded {new Date(m.uploaded_at).toLocaleDateString()}
                    </div>
                  </div>
                  {m.is_active && (
                    <span className="model-card__badge">ACTIVE</span>
                  )}
                  <div className="model-card__actions">
                    {!m.is_active && (
                      <button
                        className="model-card__btn model-card__btn--activate"
                        onClick={() => handleActivate(m.id)}
                        title="Set as active"
                      >
                        ✓
                      </button>
                    )}
                    <button
                      className="model-card__btn model-card__btn--delete"
                      onClick={() => handleDelete(m.id, m.name)}
                      title="Delete model"
                    >
                      ✕
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
