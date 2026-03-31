import math
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Detection, Camera, ModelWeight
from schemas import DetectionListResponse, DetectionResponse

router = APIRouter(prefix="/detections", tags=["Detections"])


@router.get("/", response_model=DetectionListResponse)
def list_detections(
    camera_id: Optional[int] = Query(None),
    model_id: Optional[int] = Query(None),
    label: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Detection).options(
        joinedload(Detection.camera),
        joinedload(Detection.model),
    )
    if camera_id:
        query = query.filter(Detection.camera_id == camera_id)
    if model_id:
        query = query.filter(Detection.model_id == model_id)
    if label:
        query = query.filter(Detection.label.ilike(f"%{label}%"))

    total = query.count()
    items = (
        query.order_by(Detection.timestamp.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    results = []
    for d in items:
        results.append(
            DetectionResponse(
                id=d.id,
                camera_id=d.camera_id,
                model_id=d.model_id,
                timestamp=d.timestamp,
                label=d.label,
                confidence=d.confidence,
                image_base64=d.image_base64,
                bbox_x1=d.bbox_x1,
                bbox_y1=d.bbox_y1,
                bbox_x2=d.bbox_x2,
                bbox_y2=d.bbox_y2,
                camera_name=d.camera.name if d.camera else None,
                model_name=d.model.name if d.model else None,
            )
        )

    return DetectionListResponse(
        data=results,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=math.ceil(total / per_page) if total > 0 else 1,
    )


@router.get("/stats")
def detection_stats(db: Session = Depends(get_db)):
    total = db.query(Detection).count()
    cameras = db.query(Camera).count()
    models = db.query(ModelWeight).count()
    active_streams = db.query(Camera).filter(Camera.is_streaming == True).count()

    from sqlalchemy import func
    label_counts = (
        db.query(Detection.label, func.count(Detection.id).label("count"))
        .group_by(Detection.label)
        .all()
    )
    return {
        "total_detections": total,
        "total_cameras": cameras,
        "total_models": models,
        "active_streams": active_streams,
        "label_distribution": [{"label": r[0], "count": r[1]} for r in label_counts],
    }
