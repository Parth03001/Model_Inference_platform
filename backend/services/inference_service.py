import asyncio
import base64
import threading
import time
import logging
from typing import Dict, Set, Optional
import cv2

logger = logging.getLogger(__name__)

# ── Camera workers ─────────────────────────────────────────────────────────
_camera_workers: Dict[int, "CameraWorker"] = {}
_camera_workers_lock = threading.Lock()

# ── Video workers ──────────────────────────────────────────────────────────
_video_workers: Dict[int, "VideoWorker"] = {}
_video_workers_lock = threading.Lock()

# ── WebSocket client registries (keyed by source id) ──────────────────────
_camera_ws_clients: Dict[int, Set] = {}
_video_ws_clients:  Dict[int, Set] = {}
_ws_lock = threading.Lock()

# ── Latest frames for snapshot ────────────────────────────────────────────
_camera_frames: Dict[int, Optional[str]] = {}
_video_frames:  Dict[int, Optional[str]] = {}


# ═══════════════════════════════════════════════════════════════════════════
# Public helpers — cameras
# ═══════════════════════════════════════════════════════════════════════════

def register_camera_ws(camera_id: int, ws):
    with _ws_lock:
        _camera_ws_clients.setdefault(camera_id, set()).add(ws)

def unregister_camera_ws(camera_id: int, ws):
    with _ws_lock:
        _camera_ws_clients.get(camera_id, set()).discard(ws)

def camera_is_running(camera_id: int) -> bool:
    with _camera_workers_lock:
        w = _camera_workers.get(camera_id)
        return w is not None and w.running

def start_camera_inference(camera_id: int, rtsp_url: str, model_path: str,
                            model_id: int, db_session_factory):
    with _camera_workers_lock:
        if camera_id in _camera_workers and _camera_workers[camera_id].running:
            return
        w = CameraWorker(camera_id, rtsp_url, model_path, model_id, db_session_factory)
        _camera_workers[camera_id] = w
        w.start()

def stop_camera_inference(camera_id: int):
    with _camera_workers_lock:
        w = _camera_workers.pop(camera_id, None)
    if w:
        w.stop()


# ── Legacy aliases (keeps existing stream router working unchanged) ────────
def register_ws_client(camera_id, ws):   register_camera_ws(camera_id, ws)
def unregister_ws_client(camera_id, ws): unregister_camera_ws(camera_id, ws)
def is_running(camera_id):               return camera_is_running(camera_id)
def start_inference(camera_id, rtsp_url, model_path, model_id, db_session_factory):
    start_camera_inference(camera_id, rtsp_url, model_path, model_id, db_session_factory)
def stop_inference(camera_id):           stop_camera_inference(camera_id)


# ═══════════════════════════════════════════════════════════════════════════
# Public helpers — videos
# ═══════════════════════════════════════════════════════════════════════════

def register_video_ws(video_id: int, ws):
    with _ws_lock:
        _video_ws_clients.setdefault(video_id, set()).add(ws)

def unregister_video_ws(video_id: int, ws):
    with _ws_lock:
        _video_ws_clients.get(video_id, set()).discard(ws)

def video_is_running(video_id: int) -> bool:
    with _video_workers_lock:
        w = _video_workers.get(video_id)
        return w is not None and w.running

def start_video_inference(video_id: int, file_path: str, model_path: str,
                           model_id: int, db_session_factory, loop: bool = False):
    with _video_workers_lock:
        if video_id in _video_workers and _video_workers[video_id].running:
            return
        w = VideoWorker(video_id, file_path, model_path, model_id,
                        db_session_factory, loop=loop)
        _video_workers[video_id] = w
        w.start()

def stop_video_inference(video_id: int):
    with _video_workers_lock:
        w = _video_workers.pop(video_id, None)
    if w:
        w.stop()


# ═══════════════════════════════════════════════════════════════════════════
# Shared utilities
# ═══════════════════════════════════════════════════════════════════════════

def _encode_frame(frame) -> str:
    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 65])
    return base64.b64encode(buf).decode("utf-8")


def _broadcast(ws_clients_dict: Dict, source_id: int, payload: dict):
    dead = set()
    with _ws_lock:
        clients = set(ws_clients_dict.get(source_id, []))
    for ws in clients:
        try:
            asyncio.run_coroutine_threadsafe(
                ws.send_json(payload),
                ws._loop,
            )
        except Exception:
            dead.add(ws)
    for ws in dead:
        with _ws_lock:
            ws_clients_dict.get(source_id, set()).discard(ws)


# ═══════════════════════════════════════════════════════════════════════════
# Camera Worker  (RTSP — runs forever, retries on disconnect)
# ═══════════════════════════════════════════════════════════════════════════

class CameraWorker(threading.Thread):
    def __init__(self, camera_id, rtsp_url, model_path, model_id, db_session_factory):
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.model_path = model_path
        self.model_id = model_id
        self.db_session_factory = db_session_factory
        self.running = False
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()
        self.running = False

    def _save(self, label, confidence, frame, box):
        try:
            from models import Detection
            db = self.db_session_factory()
            det = Detection(
                camera_id=self.camera_id,
                model_id=self.model_id,
                source_type="camera",
                label=label,
                confidence=float(confidence),
                image_base64=_encode_frame(frame),
                bbox_x1=float(box[0]), bbox_y1=float(box[1]),
                bbox_x2=float(box[2]), bbox_y2=float(box[3]),
            )
            db.add(det)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"[Cam {self.camera_id}] DB save error: {e}")

    def run(self):
        self.running = True
        try:
            from ultralytics import YOLO
            model = YOLO(self.model_path)
        except Exception as e:
            logger.error(f"[Cam {self.camera_id}] Model load failed: {e}")
            self.running = False
            return

        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            logger.error(f"[Cam {self.camera_id}] Cannot open {self.rtsp_url}")
            self.running = False
            return

        last_save: Dict[str, float] = {}
        logger.info(f"[Cam {self.camera_id}] Inference started.")

        while not self._stop.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"[Cam {self.camera_id}] Frame failed, reconnecting...")
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(self.rtsp_url)
                continue
            try:
                results = model(frame, conf=0.5, verbose=False)
                annotated = results[0].plot()
                for box in results[0].boxes:
                    label = model.names[int(box.cls[0])]
                    conf  = float(box.conf[0])
                    xyxy  = box.xyxy[0].tolist()
                    now = time.time()
                    if now - last_save.get(label, 0) > 30:
                        self._save(label, conf, annotated, xyxy)
                        last_save[label] = now
                _broadcast(_camera_ws_clients, self.camera_id,
                           {"type": "frame", "data": _encode_frame(annotated)})
            except Exception as e:
                logger.error(f"[Cam {self.camera_id}] Inference error: {e}")

        cap.release()
        self.running = False
        logger.info(f"[Cam {self.camera_id}] Stopped.")


# ═══════════════════════════════════════════════════════════════════════════
# Video Worker  (file — plays through once or loops, broadcasts progress)
# ═══════════════════════════════════════════════════════════════════════════

class VideoWorker(threading.Thread):
    def __init__(self, video_id, file_path, model_path, model_id,
                 db_session_factory, loop=False):
        super().__init__(daemon=True)
        self.video_id = video_id
        self.file_path = file_path
        self.model_path = model_path
        self.model_id = model_id
        self.db_session_factory = db_session_factory
        self.loop = loop
        self.running = False
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()
        self.running = False

    def _save(self, label, confidence, frame, box, frame_no, total_frames):
        try:
            from models import Detection
            db = self.db_session_factory()
            det = Detection(
                video_id=self.video_id,
                model_id=self.model_id,
                source_type="video",
                label=label,
                confidence=float(confidence),
                image_base64=_encode_frame(frame),
                bbox_x1=float(box[0]), bbox_y1=float(box[1]),
                bbox_x2=float(box[2]), bbox_y2=float(box[3]),
            )
            db.add(det)
            db.commit()
            db.close()
        except Exception as e:
            logger.error(f"[Video {self.video_id}] DB save error: {e}")

    def run(self):
        self.running = True
        try:
            from ultralytics import YOLO
            model = YOLO(self.model_path)
        except Exception as e:
            logger.error(f"[Video {self.video_id}] Model load failed: {e}")
            self.running = False
            return

        logger.info(f"[Video {self.video_id}] Inference started on {self.file_path}")

        while not self._stop.is_set():
            cap = cv2.VideoCapture(self.file_path)
            if not cap.isOpened():
                logger.error(f"[Video {self.video_id}] Cannot open file.")
                break

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
            fps = cap.get(cv2.CAP_PROP_FPS) or 25
            frame_delay = 1.0 / fps          # pace output to video FPS
            last_save: Dict[str, float] = {}
            frame_no = 0

            while not self._stop.is_set():
                t0 = time.time()
                ret, frame = cap.read()
                if not ret:
                    # End of video
                    _broadcast(_video_ws_clients, self.video_id, {"type": "ended"})
                    break

                frame_no += 1
                progress = round(frame_no / total_frames * 100, 1)

                try:
                    results = model(frame, conf=0.5, verbose=False)
                    annotated = results[0].plot()
                    for box in results[0].boxes:
                        label = model.names[int(box.cls[0])]
                        conf  = float(box.conf[0])
                        xyxy  = box.xyxy[0].tolist()
                        now = time.time()
                        if now - last_save.get(label, 0) > 5:   # save every 5s for video
                            self._save(label, conf, annotated, xyxy, frame_no, total_frames)
                            last_save[label] = now

                    _broadcast(_video_ws_clients, self.video_id, {
                        "type": "frame",
                        "data": _encode_frame(annotated),
                        "progress": progress,
                        "frame": frame_no,
                        "total": total_frames,
                    })
                except Exception as e:
                    logger.error(f"[Video {self.video_id}] Frame error: {e}")

                # Pace to video FPS so browser doesn't get flooded
                elapsed = time.time() - t0
                sleep_for = frame_delay - elapsed
                if sleep_for > 0:
                    time.sleep(sleep_for)

            cap.release()

            if not self.loop or self._stop.is_set():
                break

        self.running = False

        # Mark video as no longer processing in DB
        try:
            from models import Video
            db = self.db_session_factory()
            v = db.query(Video).filter(Video.id == self.video_id).first()
            if v:
                v.is_processing = False
                db.commit()
            db.close()
        except Exception:
            pass

        logger.info(f"[Video {self.video_id}] Finished.")
