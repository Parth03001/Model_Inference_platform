import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { listCameras, listModels, startStream, stopStream, getStreamWsUrl } from '../../services/api';
import './VideoStream.css';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit: { opacity: 0, y: -16 },
};

function StreamPanel({ camera, onStop }) {
  const [frame, setFrame] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(getStreamWsUrl(camera.id));
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'frame' && msg.data) {
          setFrame(`data:image/jpeg;base64,${msg.data}`);
        }
      } catch {}
    };

    return () => {
      ws.close();
    };
  }, [camera.id]);

  return (
    <motion.div
      className={`stream-panel ${connected ? 'stream-panel--connected' : ''}`}
      layout
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
    >
      <div className="stream-panel__header">
        <div className="stream-panel__title">
          <span className={`stream-live-dot ${connected ? 'stream-live-dot--live' : ''}`} />
          <span>{camera.name}</span>
        </div>
        <button className="stream-stop-btn" onClick={() => onStop(camera.id)}>
          ■ Stop
        </button>
      </div>
      <div className="stream-panel__body">
        {frame ? (
          <img
            className="stream-panel__frame"
            src={frame}
            alt={`Live feed from ${camera.name}`}
          />
        ) : (
          <div className="stream-panel__waiting">
            <div className="stream-panel__spinner" />
            <p>{connected ? 'Waiting for frames...' : 'Connecting...'}</p>
          </div>
        )}
        <div className="stream-panel__overlay">
          <span className={`stream-badge ${connected ? 'stream-badge--live' : 'stream-badge--idle'}`}>
            {connected ? '● LIVE' : '○ CONNECTING'}
          </span>
          <span className="stream-camera-id">ID: {camera.id}</span>
        </div>
      </div>
    </motion.div>
  );
}

export default function VideoStream() {
  const [cameras, setCameras] = useState([]);
  const [models, setModels] = useState([]);
  const [activeStreams, setActiveStreams] = useState([]);
  const [selectedCamera, setSelectedCamera] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

  const fetchData = useCallback(async () => {
    try {
      const [camRes, modRes] = await Promise.all([listCameras(), listModels()]);
      setCameras(camRes.data);
      setModels(modRes.data);
      // Restore active streams from cameras that are currently streaming
      const streaming = camRes.data.filter((c) => c.is_streaming);
      setActiveStreams((prev) => {
        const existing = new Set(prev.map((c) => c.id));
        const toAdd = streaming.filter((c) => !existing.has(c.id));
        return [...prev, ...toAdd];
      });
    } catch {
      setError('Failed to load data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleStart = async () => {
    if (!selectedCamera || !selectedModel) {
      setError('Please select a camera and a model.');
      return;
    }
    if (activeStreams.find((c) => c.id === Number(selectedCamera))) {
      setError('This camera is already streaming.');
      return;
    }
    setStarting(true);
    setError('');
    try {
      await startStream(Number(selectedCamera), Number(selectedModel));
      const cam = cameras.find((c) => c.id === Number(selectedCamera));
      if (cam) setActiveStreams((prev) => [...prev, { ...cam, is_streaming: true }]);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start stream.');
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async (cameraId) => {
    try {
      await stopStream(cameraId);
      setActiveStreams((prev) => prev.filter((c) => c.id !== cameraId));
    } catch {
      setError('Failed to stop stream.');
    }
  };

  return (
    <motion.div className="video-stream" variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <div className="page-header">
        <h1 className="page-title">Live Stream</h1>
        <p className="page-subtitle">Start inference on camera streams and watch results live</p>
      </div>

      {/* Start Stream Panel */}
      <motion.div
        className="start-stream-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <h2 className="start-stream-card__title">Start New Inference</h2>
        <div className="start-stream-form">
          <div className="form-field">
            <label className="form-label">Camera</label>
            <select
              className="form-select"
              value={selectedCamera}
              onChange={(e) => setSelectedCamera(e.target.value)}
            >
              <option value="">Select camera...</option>
              {cameras.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-field">
            <label className="form-label">Model</label>
            <select
              className="form-select"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
            >
              <option value="">Select model...</option>
              {models.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
          <motion.button
            className="start-btn"
            onClick={handleStart}
            disabled={starting || loading}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
          >
            {starting ? <span className="btn-spinner" /> : '▶ Start'}
          </motion.button>
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
        </AnimatePresence>
      </motion.div>

      {/* Active Streams Grid */}
      <div className="streams-section">
        <h2 className="section-title">
          Active Streams
          <span className="streams-count">{activeStreams.length}</span>
        </h2>

        {activeStreams.length === 0 ? (
          <div className="streams-empty">
            <span className="streams-empty__icon">▶</span>
            <p>No active streams. Start inference above.</p>
          </div>
        ) : (
          <motion.div
            className={`streams-grid streams-grid--${Math.min(activeStreams.length, 2)}`}
            layout
          >
            <AnimatePresence>
              {activeStreams.map((cam) => (
                <StreamPanel key={cam.id} camera={cam} onStop={handleStop} />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
