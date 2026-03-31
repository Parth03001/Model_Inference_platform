import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// ── Models ─────────────────────────────────────────────────────────────────
export const uploadModel = (formData) =>
  api.post('/models/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const listModels   = ()        => api.get('/models/');
export const activateModel = (id)     => api.patch(`/models/${id}/activate`);
export const deleteModel   = (id)     => api.delete(`/models/${id}`);

// ── Cameras ────────────────────────────────────────────────────────────────
export const addCamera    = (data)    => api.post('/cameras/', data);
export const listCameras  = ()        => api.get('/cameras/');
export const updateCamera = (id, data)=> api.patch(`/cameras/${id}`, data);
export const deleteCamera = (id)      => api.delete(`/cameras/${id}`);

// ── Videos ─────────────────────────────────────────────────────────────────
export const uploadVideo = (formData, onProgress) =>
  api.post('/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    },
  });
export const listVideos  = ()   => api.get('/videos/');
export const deleteVideo = (id) => api.delete(`/videos/${id}`);

// ── Camera Stream ──────────────────────────────────────────────────────────
export const startCameraStream = (camera_id, model_id) =>
  api.post('/stream/start', { camera_id, model_id });
export const stopCameraStream  = (camera_id) =>
  api.post('/stream/stop', { camera_id });
export const getCameraStreamStatus = (camera_id) =>
  api.get(`/stream/status/${camera_id}`);

// ── Video Stream ───────────────────────────────────────────────────────────
export const startVideoStream = (video_id, model_id, loop = false) =>
  api.post('/stream/video/start', { video_id, model_id, loop });
export const stopVideoStream  = (video_id) =>
  api.post('/stream/video/stop', { video_id });
export const getVideoStreamStatus = (video_id) =>
  api.get(`/stream/video/status/${video_id}`);

// Legacy alias so existing components don't break
export const startStream = startCameraStream;
export const stopStream  = stopCameraStream;
export const getStreamStatus = getCameraStreamStatus;

// ── Detections ─────────────────────────────────────────────────────────────
export const listDetections = (params) => api.get('/detections/', { params });
export const getStats       = ()        => api.get('/detections/stats');

// ── WebSocket URLs ─────────────────────────────────────────────────────────
export const WS_BASE_URL = BASE_URL.replace(/^http/, 'ws');
export const getCameraWsUrl = (camera_id) => `${WS_BASE_URL}/stream/ws/${camera_id}`;
export const getVideoWsUrl  = (video_id)  => `${WS_BASE_URL}/stream/ws/video/${video_id}`;

// Legacy alias
export const getStreamWsUrl = getCameraWsUrl;

export default api;
