import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from database import get_db
from models import ModelWeight
from schemas import ModelWeightResponse

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/models", tags=["Models"])


@router.post("/upload", response_model=ModelWeightResponse)
async def upload_model(
    name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith((".pt", ".engine", ".onnx")):
        raise HTTPException(status_code=400, detail="Only .pt, .engine, or .onnx weight files are allowed.")

    dest_path = os.path.join(UPLOAD_DIR, file.filename)
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(file.filename)
        import time
        dest_path = os.path.join(UPLOAD_DIR, f"{base}_{int(time.time())}{ext}")

    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    model = ModelWeight(
        name=name,
        filename=os.path.basename(dest_path),
        file_path=dest_path,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


@router.get("/", response_model=List[ModelWeightResponse])
def list_models(db: Session = Depends(get_db)):
    return db.query(ModelWeight).order_by(ModelWeight.uploaded_at.desc()).all()


@router.get("/{model_id}", response_model=ModelWeightResponse)
def get_model(model_id: int, db: Session = Depends(get_db)):
    model = db.query(ModelWeight).filter(ModelWeight.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.patch("/{model_id}/activate", response_model=ModelWeightResponse)
def activate_model(model_id: int, db: Session = Depends(get_db)):
    db.query(ModelWeight).update({ModelWeight.is_active: False})
    model = db.query(ModelWeight).filter(ModelWeight.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    model.is_active = True
    db.commit()
    db.refresh(model)
    return model


@router.delete("/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    model = db.query(ModelWeight).filter(ModelWeight.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if os.path.exists(model.file_path):
        os.remove(model.file_path)
    db.delete(model)
    db.commit()
    return {"message": "Model deleted successfully"}
