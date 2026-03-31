from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# ── ModelWeight ────────────────────────────────────────────────────────────
class ModelWeightBase(BaseModel):
    name: str

class ModelWeightCreate(ModelWeightBase):
    pass

class ModelWeightResponse(ModelWeightBase):
    id: int
    filename: str
    file_path: str
    uploaded_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# ── Camera ─────────────────────────────────────────────────────────────────
class CameraBase(BaseModel):
    name: str
    rtsp_url: str

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    is_active: Optional[bool] = None

class CameraResponse(CameraBase):
    id: int
    is_active: bool
    is_streaming: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Video ──────────────────────────────────────────────────────────────────
class VideoResponse(BaseModel):
    id: int
    name: str
    filename: str
    file_path: str
    duration: Optional[float] = None
    file_size: Optional[float] = None
    uploaded_at: datetime
    is_processing: bool

    class Config:
        from_attributes = True


# ── Detection ──────────────────────────────────────────────────────────────
class DetectionResponse(BaseModel):
    id: int
    camera_id: Optional[int] = None
    video_id: Optional[int] = None
    model_id: int
    source_type: str
    timestamp: datetime
    label: str
    confidence: float
    image_base64: Optional[str] = None
    bbox_x1: Optional[float] = None
    bbox_y1: Optional[float] = None
    bbox_x2: Optional[float] = None
    bbox_y2: Optional[float] = None
    camera_name: Optional[str] = None
    video_name: Optional[str] = None
    model_name: Optional[str] = None

    class Config:
        from_attributes = True

class DetectionListResponse(BaseModel):
    data: List[DetectionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# ── Stream requests ────────────────────────────────────────────────────────
class InferenceStartRequest(BaseModel):
    camera_id: int
    model_id: int

class InferenceStopRequest(BaseModel):
    camera_id: int

class VideoInferenceStartRequest(BaseModel):
    video_id: int
    model_id: int
    loop: bool = False          # replay video when it ends

class VideoInferenceStopRequest(BaseModel):
    video_id: int
