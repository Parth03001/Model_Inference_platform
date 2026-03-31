from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


# --- ModelWeight Schemas ---
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


# --- Camera Schemas ---
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


# --- Detection Schemas ---
class DetectionResponse(BaseModel):
    id: int
    camera_id: int
    model_id: int
    timestamp: datetime
    label: str
    confidence: float
    image_base64: Optional[str] = None
    bbox_x1: Optional[float] = None
    bbox_y1: Optional[float] = None
    bbox_x2: Optional[float] = None
    bbox_y2: Optional[float] = None
    camera_name: Optional[str] = None
    model_name: Optional[str] = None

    class Config:
        from_attributes = True


class DetectionListResponse(BaseModel):
    data: List[DetectionResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class InferenceStartRequest(BaseModel):
    camera_id: int
    model_id: int


class InferenceStopRequest(BaseModel):
    camera_id: int
