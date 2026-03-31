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


class Detection(Base):
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("model_weights.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    label = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    image_base64 = Column(Text, nullable=True)
    bbox_x1 = Column(Float, nullable=True)
    bbox_y1 = Column(Float, nullable=True)
    bbox_x2 = Column(Float, nullable=True)
    bbox_y2 = Column(Float, nullable=True)

    camera = relationship("Camera", back_populates="detections")
    model = relationship("ModelWeight", back_populates="detections")
