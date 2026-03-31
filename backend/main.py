import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import engine, Base
from routers import cameras, model_upload, detections, stream, videos

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Model Inference Platform",
    description="Upload YOLO weights, add camera RTSP streams, run real-time inference, store results in PostgreSQL.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
def on_startup():
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    os.makedirs(os.getenv("UPLOAD_DIR", "uploads"), exist_ok=True)
    logger.info("Startup complete.")

app.include_router(cameras.router)
app.include_router(model_upload.router)
app.include_router(videos.router)
app.include_router(detections.router)
app.include_router(stream.router)


@app.get("/")
def root():
    return {"message": "Model Inference Platform API is running", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
