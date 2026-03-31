import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Models
export const uploadModel = (formData) =>
  api.post('/models/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const listModels = () => api.get('/models/');
export const activateModel = (id) => api.patch(`/models/${id}/activate`);
export const deleteModel = (id) => api.delete(`/models/${id}`);

// Cameras
export const addCamera = (data) => api.post('/cameras/', data);
export const listCameras = () => api.get('/cameras/');
export const updateCamera = (id, data) => api.patch(`/cameras/${id}`, data);
export const deleteCamera = (id) => api.delete(`/cameras/${id}`);

// Stream
export const startStream = (camera_id, model_id) =>
  api.post('/stream/start', { camera_id, model_id });
export const stopStream = (camera_id) =>
  api.post('/stream/stop', { camera_id });
export const getStreamStatus = (camera_id) =>
  api.get(`/stream/status/${camera_id}`);

// Detections
export const listDetections = (params) => api.get('/detections/', { params });
export const getStats = () => api.get('/detections/stats');

export const WS_BASE_URL = BASE_URL.replace(/^http/, 'ws');
export const getStreamWsUrl = (camera_id) => `${WS_BASE_URL}/stream/ws/${camera_id}`;

export default api;
