from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class ModelWeight(Base):
    __tablename__ = "model_weights"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)

    detections = relationship("Detection", back_populates="model")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    is_streaming = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    detections = relationship("Detection", back_populates="camera")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    duration = Column(Float, nullable=True)       # seconds, filled after upload
    file_size = Column(Float, nullable=True)      # bytes
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_processing = Column(Boolean, default=False)

    detections = relationship("Detection", back_populates="video")


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    # Either camera_id OR video_id is set — not both
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=True)
    video_id  = Column(Integer, ForeignKey("videos.id"),  nullable=True)
    model_id  = Column(Integer, ForeignKey("model_weights.id"), nullable=False)
    source_type = Column(String(10), nullable=False, default="camera")  # "camera" | "video"
    timestamp = Column(DateTime, default=datetime.utcnow)
    label = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    image_base64 = Column(Text, nullable=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)

    camera = relationship("Camera", back_populates="detections")
    video  = relationship("Video",  back_populates="detections")
    model  = relationship("ModelWeight", back_populates="detections")
