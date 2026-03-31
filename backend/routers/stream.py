import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import Camera, ModelWeight, Video
from schemas import (
    InferenceStartRequest, InferenceStopRequest,
    VideoInferenceStartRequest, VideoInferenceStopRequest,
)
from services import inference_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stream", tags=["Stream"])


# ══════════════════════════════════════════════════════════════════════════
# Camera stream endpoints
# ══════════════════════════════════════════════════════════════════════════

@router.post("/start")
def start_camera_stream(payload: InferenceStartRequest, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    model = db.query(ModelWeight).filter(ModelWeight.id == payload.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if inference_service.camera_is_running(payload.camera_id):
        return {"message": "Inference already running for this camera"}

    camera.is_streaming = True
    db.commit()

    inference_service.start_camera_inference(
        camera_id=camera.id,
        rtsp_url=camera.rtsp_url,
        model_path=model.file_path,
        model_id=model.id,
        db_session_factory=SessionLocal,
    )
    return {"message": f"Inference started for camera '{camera.name}'"}


@router.post("/stop")
def stop_camera_stream(payload: InferenceStopRequest, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    inference_service.stop_camera_inference(payload.camera_id)
    camera.is_streaming = False
    db.commit()
    return {"message": f"Inference stopped for camera '{camera.name}'"}


@router.get("/status/{camera_id}")
def camera_stream_status(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return {"camera_id": camera_id, "is_running": inference_service.camera_is_running(camera_id)}


@router.websocket("/ws/{camera_id}")
async def camera_ws(websocket: WebSocket, camera_id: int):
    await websocket.accept()
    websocket._loop = asyncio.get_event_loop()
    inference_service.register_camera_ws(camera_id, websocket)
    logger.info(f"Camera WS connected: {camera_id}")
    try:
        while True:
            await asyncio.sleep(0.5)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        inference_service.unregister_camera_ws(camera_id, websocket)
        logger.info(f"Camera WS disconnected: {camera_id}")


# ══════════════════════════════════════════════════════════════════════════
# Video stream endpoints
# ══════════════════════════════════════════════════════════════════════════

@router.post("/video/start")
def start_video_stream(payload: VideoInferenceStartRequest, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    model = db.query(ModelWeight).filter(ModelWeight.id == payload.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if inference_service.video_is_running(payload.video_id):
        return {"message": "Inference already running for this video"}

    video.is_processing = True
    db.commit()

    inference_service.start_video_inference(
        video_id=video.id,
        file_path=video.file_path,
        model_path=model.file_path,
        model_id=model.id,
        db_session_factory=SessionLocal,
        loop=payload.loop,
    )
    return {"message": f"Inference started for video '{video.name}'"}


@router.post("/video/stop")
def stop_video_stream(payload: VideoInferenceStopRequest, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == payload.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    inference_service.stop_video_inference(payload.video_id)
    video.is_processing = False
    db.commit()
    return {"message": f"Inference stopped for video '{video.name}'"}


@router.get("/video/status/{video_id}")
def video_stream_status(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return {"video_id": video_id, "is_running": inference_service.video_is_running(video_id)}


@router.websocket("/ws/video/{video_id}")
async def video_ws(websocket: WebSocket, video_id: int):
    await websocket.accept()
    websocket._loop = asyncio.get_event_loop()
    inference_service.register_video_ws(video_id, websocket)
    logger.info(f"Video WS connected: {video_id}")
    try:
        while True:
            await asyncio.sleep(0.5)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        inference_service.unregister_video_ws(video_id, websocket)
        logger.info(f"Video WS disconnected: {video_id}")
