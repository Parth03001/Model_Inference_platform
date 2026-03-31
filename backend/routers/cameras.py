from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Camera
from schemas import CameraCreate, CameraResponse, CameraUpdate

router = APIRouter(prefix="/cameras", tags=["Cameras"])


@router.post("/", response_model=CameraResponse)
def add_camera(payload: CameraCreate, db: Session = Depends(get_db)):
    camera = Camera(name=payload.name, rtsp_url=payload.rtsp_url)
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


@router.get("/", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).order_by(Camera.created_at.desc()).all()


@router.get("/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera


@router.patch("/{camera_id}", response_model=CameraResponse)
def update_camera(camera_id: int, payload: CameraUpdate, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(camera, field, value)
    db.commit()
    db.refresh(camera)
    return camera


@router.delete("/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(camera)
    db.commit()
    return {"message": "Camera deleted successfully"}
