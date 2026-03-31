import React, { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  listCameras, listModels, listVideos,
  startCameraStream, stopCameraStream,
  startVideoStream, stopVideoStream,
  getCameraWsUrl, getVideoWsUrl,
} from '../../services/api';
import './VideoStream.css';

const pageVariants = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
  exit:    { opacity: 0, y: -16 },
};

// ── Individual stream panel (works for both camera and video) ──────────────
function StreamPanel({ source, sourceType, onStop }) {
  const [frame, setFrame]         = useState(null);
  const [connected, setConnected] = useState(false);
  const [progress, setProgress]   = useState(null);  // for video
  const [ended, setEnded]         = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    const url = sourceType === 'video'
      ? getVideoWsUrl(source.id)
      : getCameraWsUrl(source.id);

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen  = () => { setConnected(true); setEnded(false); };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'frame' && msg.data) {
          setFrame(`data:image/jpeg;base64,${msg.data}`);
          if (msg.progress != null) setProgress(msg.progress);
        } else if (msg.type === 'ended') {
          setEnded(true);
        }
      } catch {}
    };

    return () => ws.close();
  }, [source.id, sourceType]);

  const isVideo = sourceType === 'video';

  return (
    <motion.div
      className={`stream-panel ${connected ? 'stream-panel--connected' : ''} ${ended ? 'stream-panel--ended' : ''}`}
      layout
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
    >
      {/* Header */}
      <div className="stream-panel__header">
        <div className="stream-panel__title">
          <span className={`stream-live-dot ${connected && !ended ? 'stream-live-dot--live' : ''}`} />
          <span className="stream-source-tag">{isVideo ? '▶ VIDEO' : '◎ CAMERA'}</span>
          <span>{source.name}</span>
        </div>
        <button className="stream-stop-btn" onClick={() => onStop(source.id, sourceType)}>
          ■ Stop
        </button>
      </div>

      {/* Video progress bar */}
      {isVideo && progress != null && (
        <div className="stream-progress-bar">
          <motion.div
            className="stream-progress-fill"
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.3 }}
          />
          <span className="stream-progress-label">{progress}%</span>
        </div>
      )}

      {/* Frame */}
      <div className="stream-panel__body">
        {ended ? (
          <div className="stream-panel__ended">
            <span className="stream-ended-icon">■</span>
            <p>Video finished</p>
          </div>
        ) : frame ? (
          <img className="stream-panel__frame" src={frame} alt={`Feed — ${source.name}`} />
        ) : (
          <div className="stream-panel__waiting">
            <div className="stream-panel__spinner" />
            <p>{connected ? 'Waiting for frames...' : 'Connecting...'}</p>
          </div>
        )}

        <div className="stream-panel__overlay">
          <span className={`stream-badge ${connected && !ended ? 'stream-badge--live' : 'stream-badge--idle'}`}>
            {ended ? '■ ENDED' : connected ? '● LIVE' : '○ CONNECTING'}
          </span>
          <span className="stream-source-id">ID: {source.id}</span>
        </div>
      </div>
    </motion.div>
  );
}


// ── Main page ──────────────────────────────────────────────────────────────
export default function VideoStream() {
  const [tab, setTab]               = useState('camera');  // 'camera' | 'video'
  const [cameras, setCameras]       = useState([]);
  const [videos, setVideos]         = useState([]);
  const [models, setModels]         = useState([]);
  const [activePanels, setActivePanels] = useState([]); // { source, sourceType }
  const [selCamera, setSelCamera]   = useState('');
  const [selVideo, setSelVideo]     = useState('');
  const [selModel, setSelModel]     = useState('');
  const [loopVideo, setLoopVideo]   = useState(false);
  const [loading, setLoading]       = useState(true);
  const [starting, setStarting]     = useState(false);
  const [error, setError]           = useState('');

  const fetchData = useCallback(async () => {
    try {
      const [camRes, modRes, vidRes] = await Promise.all([
        listCameras(), listModels(), listVideos(),
      ]);
      setCameras(camRes.data);
      setModels(modRes.data);
      setVideos(vidRes.data);
      // Restore camera panels already streaming
      const streaming = camRes.data.filter((c) => c.is_streaming);
      setActivePanels((prev) => {
        const existing = new Set(prev.map((p) => `${p.sourceType}-${p.source.id}`));
        const toAdd = streaming
          .filter((c) => !existing.has(`camera-${c.id}`))
          .map((c) => ({ source: c, sourceType: 'camera' }));
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
    setError('');
    const isCamera = tab === 'camera';

    if (!selModel) { setError('Please select a model.'); return; }
    if (isCamera && !selCamera) { setError('Please select a camera.'); return; }
    if (!isCamera && !selVideo) { setError('Please select a video.'); return; }

    const sourceId = isCamera ? Number(selCamera) : Number(selVideo);
    const sourceType = isCamera ? 'camera' : 'video';
    const alreadyActive = activePanels.find(
      (p) => p.sourceType === sourceType && p.source.id === sourceId
    );
    if (alreadyActive) { setError('Already streaming this source.'); return; }

    setStarting(true);
    try {
      if (isCamera) {
        await startCameraStream(sourceId, Number(selModel));
        const src = cameras.find((c) => c.id === sourceId);
        setActivePanels((p) => [...p, { source: { ...src, is_streaming: true }, sourceType: 'camera' }]);
      } else {
        await startVideoStream(sourceId, Number(selModel), loopVideo);
        const src = videos.find((v) => v.id === sourceId);
        setActivePanels((p) => [...p, { source: { ...src, is_processing: true }, sourceType: 'video' }]);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start inference.');
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async (sourceId, sourceType) => {
    try {
      if (sourceType === 'camera') await stopCameraStream(sourceId);
      else                          await stopVideoStream(sourceId);
      setActivePanels((p) => p.filter(
        (x) => !(x.sourceType === sourceType && x.source.id === sourceId)
      ));
    } catch {
      setError('Failed to stop stream.');
    }
  };

  return (
    <motion.div className="video-stream" variants={pageVariants} initial="initial" animate="animate" exit="exit">
      <div className="page-header">
        <h1 className="page-title">Live Stream</h1>
        <p className="page-subtitle">Run inference on camera RTSP streams or uploaded video files</p>
      </div>

      {/* Control panel */}
      <motion.div
        className="stream-control-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {/* Source type tabs */}
        <div className="stream-tabs">
          <button
            className={`stream-tab ${tab === 'camera' ? 'stream-tab--active' : ''}`}
            onClick={() => setTab('camera')}
          >
            <span>◎</span> Camera Stream
          </button>
          <button
            className={`stream-tab ${tab === 'video' ? 'stream-tab--active' : ''}`}
            onClick={() => setTab('video')}
          >
            <span>▶</span> Video File
          </button>
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            className="stream-form"
            initial={{ opacity: 0, x: tab === 'camera' ? -12 : 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {tab === 'camera' ? (
              <div className="form-field">
                <label className="form-label">Camera</label>
                <select className="form-select" value={selCamera} onChange={(e) => setSelCamera(e.target.value)}>
                  <option value="">Select camera...</option>
                  {cameras.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
            ) : (
              <>
                <div className="form-field">
                  <label className="form-label">Video File</label>
                  <select className="form-select" value={selVideo} onChange={(e) => setSelVideo(e.target.value)}>
                    <option value="">Select video...</option>
                    {videos.map((v) => (
                      <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                  </select>
                </div>
                <div className="form-field form-field--checkbox">
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={loopVideo}
                      onChange={(e) => setLoopVideo(e.target.checked)}
                    />
                    <span>Loop video</span>
                  </label>
                </div>
              </>
            )}

            <div className="form-field">
              <label className="form-label">Model</label>
              <select className="form-select" value={selModel} onChange={(e) => setSelModel(e.target.value)}>
                <option value="">Select model...</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            <motion.button
              className={`start-btn start-btn--${tab}`}
              onClick={handleStart}
              disabled={starting || loading}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
            >
              {starting ? <span className="btn-spinner" /> : tab === 'camera' ? '◎ Start Camera' : '▶ Run on Video'}
            </motion.button>
          </motion.div>
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.p className="form-error"
              initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}>
              {error}
            </motion.p>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Active stream panels */}
      <div className="streams-section">
        <h2 className="section-title">
          Active Streams
          <span className="streams-count">{activePanels.length}</span>
        </h2>

        {activePanels.length === 0 ? (
          <div className="streams-empty">
            <span className="streams-empty__icon">▶</span>
            <p>No active streams. Start a camera or video inference above.</p>
          </div>
        ) : (
          <motion.div
            className={`streams-grid streams-grid--${Math.min(activePanels.length, 2)}`}
            layout
          >
            <AnimatePresence>
              {activePanels.map((panel) => (
                <StreamPanel
                  key={`${panel.sourceType}-${panel.source.id}`}
                  source={panel.source}
                  sourceType={panel.sourceType}
                  onStop={handleStop}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}
