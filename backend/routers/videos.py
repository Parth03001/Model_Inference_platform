import os
import shutil
import time
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import cv2

from database import get_db
from models import Video
from schemas import VideoResponse

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
VIDEO_DIR = os.path.join(UPLOAD_DIR, "videos")
os.makedirs(VIDEO_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm")

router = APIRouter(prefix="/videos", tags=["Videos"])


def _get_video_meta(path: str):
    """Return (duration_seconds, file_size_bytes) for a video file."""
    try:
        cap = cv2.VideoCapture(path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 1
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps
        cap.release()
    except Exception:
        duration = None
    size = os.path.getsize(path) if os.path.exists(path) else None
    return duration, size


@router.post("/upload", response_model=VideoResponse)
async def upload_video(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    safe_filename = file.filename
    dest_path = os.path.join(VIDEO_DIR, safe_filename)
    if os.path.exists(dest_path):
        base, extension = os.path.splitext(safe_filename)
        safe_filename = f"{base}_{int(time.time())}{extension}"
        dest_path = os.path.join(VIDEO_DIR, safe_filename)

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    duration, size = _get_video_meta(dest_path)

    video = Video(
        name=name,
        filename=safe_filename,
        file_path=dest_path,
        duration=duration,
        file_size=size,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    return video


@router.get("/", response_model=List[VideoResponse])
def list_videos(db: Session = Depends(get_db)):
    return db.query(Video).order_by(Video.uploaded_at.desc()).all()


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.delete("/{video_id}")
def delete_video(video_id: int, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    if os.path.exists(video.file_path):
        os.remove(video.file_path)
    db.delete(video)
    db.commit()
    return {"message": "Video deleted successfully"}
