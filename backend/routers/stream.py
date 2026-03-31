import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, SessionLocal
from models import Camera, ModelWeight
from schemas import InferenceStartRequest, InferenceStopRequest
from services import inference_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stream", tags=["Stream"])


@router.post("/start")
def start_stream(payload: InferenceStartRequest, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    model = db.query(ModelWeight).filter(ModelWeight.id == payload.model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if inference_service.is_running(payload.camera_id):
        return {"message": "Inference already running for this camera"}

    camera.is_streaming = True
    db.commit()

    inference_service.start_inference(
        camera_id=camera.id,
        rtsp_url=camera.rtsp_url,
        model_path=model.file_path,
        model_id=model.id,
        db_session_factory=SessionLocal,
    )
    return {"message": f"Inference started for camera '{camera.name}'"}


@router.post("/stop")
def stop_stream(payload: InferenceStopRequest, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    inference_service.stop_inference(payload.camera_id)
    camera.is_streaming = False
    db.commit()
    return {"message": f"Inference stopped for camera '{camera.name}'"}


@router.get("/status/{camera_id}")
def stream_status(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    running = inference_service.is_running(camera_id)
    return {"camera_id": camera_id, "is_running": running}


@router.websocket("/ws/{camera_id}")
async def websocket_stream(websocket: WebSocket, camera_id: int):
    await websocket.accept()
    # Attach event loop reference so inference thread can schedule sends
    websocket._loop = asyncio.get_event_loop()
    inference_service.register_ws_client(camera_id, websocket)
    logger.info(f"WebSocket client connected for camera {camera_id}")
    try:
        while True:
            # Keep connection alive; inference thread pushes frames
            await asyncio.sleep(0.5)
            # Send a ping to detect disconnects
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        inference_service.unregister_ws_client(camera_id, websocket)
        logger.info(f"WebSocket client disconnected for camera {camera_id}")
