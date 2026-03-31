import React, { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadVideo, listVideos, deleteVideo } from '../../services/api';
import './VideoUpload.css';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit:    { opacity: 0, y: -16 },
};

function formatDuration(secs) {
  if (!secs) return '—';
  const m = Math.floor(secs / 60);
  const s = Math.round(secs % 60);
  return `${m}m ${s}s`;
}

function formatSize(bytes) {
  if (!bytes) return '—';
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / (1024 ** 3)).toFixed(1)} GB`;
  if (bytes >= 1024 * 1024)        return `${(bytes / (1024 ** 2)).toFixed(1)} MB`;
  return `${(bytes / 1024).toFixed(0)} KB`;
}

export default function VideoUpload() {
  const [videos, setVideos]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadPct, setUploadPct] = useState(0);
  const [error, setError]         = useState('');
  const [success, setSuccess]     = useState('');
  const [videoName, setVideoName] = useState('');
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragging, setDragging]   = useState(false);
  const fileRef = useRef(null);

  const fetchVideos = useCallback(async () => {
    try {
      const res = await listVideos();
      setVideos(res.data);
    } catch {
      setError('Failed to load videos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchVideos(); }, [fetchVideos]);

  const handleFile = (file) => {
    if (!file) return;
    const allowed = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowed.includes(ext)) {
      setError(`Only video files allowed: ${allowed.join(', ')}`);
      return;
    }
    setSelectedFile(file);
    setError('');
    if (!videoName) setVideoName(file.name.replace(/\.[^.]+$/, ''));
  };

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  }, [videoName]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile || !videoName.trim()) {
      setError('Please provide a name and select a video file.');
      return;
    }
    const formData = new FormData();
    formData.append('name', videoName.trim());
    formData.append('file', selectedFile);
    setUploading(true);
    setUploadPct(0);
    setError('');
    try {
      await uploadVideo(formData, (pct) => setUploadPct(pct));
      setSuccess(`"${videoName}" uploaded successfully!`);
      setVideoName('');
      setSelectedFile(null);
      fetchVideos();
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed.');
    } finally {
      setUploading(false);
      setUploadPct(0);
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete video "${name}"?`)) return;
    try {
      await deleteVideo(id);
      setVideos((v) => v.filter((x) => x.id !== id));
    } catch {
      setError('Failed to delete video.');
    }
  };

  return (
    <motion.div className="video-upload" variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <div className="page-header">
        <h1 className="page-title">Video Files</h1>
        <p className="page-subtitle">Upload video files and run YOLO inference on them</p>
      </div>

      {/* Upload card */}
      <motion.div
        className="upload-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <h2 className="upload-card__title">Upload Video</h2>
        <form onSubmit={handleSubmit} className="upload-form">
          <div className="form-field">
            <label className="form-label">Video Name</label>
            <input
              className="form-input"
              type="text"
              placeholder="e.g. Factory Floor Recording 01"
              value={videoName}
              onChange={(e) => setVideoName(e.target.value)}
            />
          </div>

          <div
            className={`dropzone ${dragging ? 'dropzone--active' : ''} ${selectedFile ? 'dropzone--has-file' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".mp4,.avi,.mov,.mkv,.wmv,.flv,.webm"
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
                  <span className="dropzone__file-icon">▶</span>
                  <span className="dropzone__file-name">{selectedFile.name}</span>
                  <span className="dropzone__file-size">{formatSize(selectedFile.size)}</span>
                </motion.div>
              ) : (
                <motion.div
                  key="empty"
                  className="dropzone__placeholder"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                >
                  <span className="dropzone__icon">▶</span>
                  <span className="dropzone__text">Drop your video file here</span>
                  <span className="dropzone__hint">.mp4 · .avi · .mov · .mkv · .wmv · .webm</span>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Progress bar */}
          <AnimatePresence>
            {uploading && (
              <motion.div
                className="upload-progress"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
              >
                <div className="upload-progress__bar">
                  <motion.div
                    className="upload-progress__fill"
                    animate={{ width: `${uploadPct}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
                <span className="upload-progress__label">{uploadPct}% uploaded</span>
              </motion.div>
            )}
            {error && (
              <motion.p className="form-error"
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                {error}
              </motion.p>
            )}
            {success && (
              <motion.p className="form-success"
                initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
                {success}
              </motion.p>
            )}
          </AnimatePresence>

          <motion.button
            className="btn-submit"
            type="submit"
            disabled={uploading}
            whileHover={{ scale: uploading ? 1 : 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {uploading ? <span className="btn-spinner" /> : '⬆ Upload Video'}
          </motion.button>
        </form>
      </motion.div>

      {/* Videos list */}
      <div className="videos-section">
        <h2 className="section-title">Uploaded Videos ({videos.length})</h2>
        {loading ? (
          <div className="videos-loading">
            {[1, 2, 3].map((i) => <div key={i} className="video-skeleton" />)}
          </div>
        ) : videos.length === 0 ? (
          <div className="videos-empty">
            <span className="videos-empty__icon">▶</span>
            <p>No videos uploaded yet.</p>
          </div>
        ) : (
          <motion.div className="videos-grid" layout>
            <AnimatePresence>
              {videos.map((v, i) => (
                <motion.div
                  key={v.id}
                  className={`video-card ${v.is_processing ? 'video-card--processing' : ''}`}
                  layout
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: i * 0.05 } }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  whileHover={{ y: -4 }}
                >
                  <div className="video-card__thumb">
                    <span className="video-card__play">▶</span>
                    {v.is_processing && (
                      <div className="video-card__processing-badge">Processing...</div>
                    )}
                  </div>
                  <div className="video-card__info">
                    <div className="video-card__name">{v.name}</div>
                    <div className="video-card__file">{v.filename}</div>
                    <div className="video-card__meta">
                      <span>⏱ {formatDuration(v.duration)}</span>
                      <span>💾 {formatSize(v.file_size)}</span>
                      <span>{new Date(v.uploaded_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <button
                    className="video-card__delete"
                    onClick={() => handleDelete(v.id, v.name)}
                    title="Delete video"
                  >
                    ✕
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
