import asyncio
import base64
import threading
import time
import logging
from datetime import datetime
from typing import Dict, Set, Optional
import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Registry: camera_id -> InferenceWorker
_workers: Dict[int, "InferenceWorker"] = {}
_workers_lock = threading.Lock()

# WebSocket clients: camera_id -> set of websocket connections
_ws_clients: Dict[int, Set] = {}
_ws_clients_lock = threading.Lock()

# Per-camera latest frame (base64 JPEG) for snapshot requests
_latest_frames: Dict[int, Optional[str]] = {}


def register_ws_client(camera_id: int, ws):
    with _ws_clients_lock:
        if camera_id not in _ws_clients:
            _ws_clients[camera_id] = set()
        _ws_clients[camera_id].add(ws)


def unregister_ws_client(camera_id: int, ws):
    with _ws_clients_lock:
        if camera_id in _ws_clients:
            _ws_clients[camera_id].discard(ws)


def get_latest_frame(camera_id: int) -> Optional[str]:
    return _latest_frames.get(camera_id)


def is_running(camera_id: int) -> bool:
    with _workers_lock:
        w = _workers.get(camera_id)
        return w is not None and w.running


def start_inference(camera_id: int, rtsp_url: str, model_path: str, model_id: int, db_session_factory):
    with _workers_lock:
        if camera_id in _workers and _workers[camera_id].running:
            return  # already running
        worker = InferenceWorker(camera_id, rtsp_url, model_path, model_id, db_session_factory)
        _workers[camera_id] = worker
        worker.start()


def stop_inference(camera_id: int):
    with _workers_lock:
        worker = _workers.pop(camera_id, None)
    if worker:
        worker.stop()


class InferenceWorker(threading.Thread):
    def __init__(self, camera_id: int, rtsp_url: str, model_path: str, model_id: int, db_session_factory):
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.model_path = model_path
        self.model_id = model_id
        self.db_session_factory = db_session_factory
        self.running = False
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()
        self.running = False

    def _encode_frame(self, frame) -> str:
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        return base64.b64encode(buf).decode("utf-8")

    def _save_detection(self, label: str, confidence: float, frame, box):
        try:
            from models import Detection
            db = self.db_session_factory()
            img_b64 = self._encode_frame(frame)
            det = Detection(
                camera_id=self.camera_id,
                model_id=self.model_id,
                label=label,
                confidence=float(confidence),
                image_base64=img_b64,
                bbox_x1=float(box[0]),
                bbox_y1=float(box[1]),
                bbox_x2=float(box[2]),
                bbox_y2=float(box[3]),
            )
            db.add(det)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"Failed to save detection: {e}")

    def _broadcast_frame(self, frame_b64: str):
        _latest_frames[self.camera_id] = frame_b64
        dead = set()
        with _ws_clients_lock:
            clients = set(_ws_clients.get(self.camera_id, []))
        for ws in clients:
            try:
                asyncio.run_coroutine_threadsafe(
                    ws.send_json({"type": "frame", "data": frame_b64}),
                    ws._loop,
                )
            except Exception:
                dead.add(ws)
        for ws in dead:
            unregister_ws_client(self.camera_id, ws)

    def run(self):
        self.running = True
        logger.info(f"[Camera {self.camera_id}] Loading model from {self.model_path}")
        try:
            from ultralytics import YOLO
            model = YOLO(self.model_path)
        except Exception as e:
            logger.error(f"[Camera {self.camera_id}] Failed to load model: {e}")
            self.running = False
            return

        logger.info(f"[Camera {self.camera_id}] Connecting to {self.rtsp_url}")
        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            logger.error(f"[Camera {self.camera_id}] Cannot open stream {self.rtsp_url}")
            self.running = False
            return

        logger.info(f"[Camera {self.camera_id}] Stream opened. Inference running.")
        last_save_time: Dict[str, float] = {}

        while not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"[Camera {self.camera_id}] Frame read failed, retrying...")
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(self.rtsp_url)
                continue

            try:
                results = model(frame, conf=0.5, verbose=False)
                annotated = results[0].plot()

                for box in results[0].boxes:
                    cls_id = int(box.cls[0])
                    label = model.names[cls_id]
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].tolist()

                    # Throttle saves per label: one per 30s
                    now = time.time()
                    if now - last_save_time.get(label, 0) > 30:
                        self._save_detection(label, conf, annotated, xyxy)
                        last_save_time[label] = now

                frame_b64 = self._encode_frame(annotated)
                self._broadcast_frame(frame_b64)

            except Exception as e:
                logger.error(f"[Camera {self.camera_id}] Inference error: {e}")

        cap.release()
        self.running = False
        logger.info(f"[Camera {self.camera_id}] Inference stopped.")
