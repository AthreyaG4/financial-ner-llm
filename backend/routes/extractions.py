from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from db import get_db
from models import Extraction, ExtractionStatus
from schemas import ExtractionRead
from utils.placeholders import simulate_llamaparse, simulate_vllm_extraction

router = APIRouter(prefix="/api/extractions", tags=["extractions"])

NOT_READY_FOR_EXTRACT = {
    ExtractionStatus.PARSING,
    ExtractionStatus.PARSE_FAILED,
    ExtractionStatus.EXTRACTING,
}


@router.post("", response_model=ExtractionRead, status_code=201)
def create_extraction(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    extraction = Extraction(file_name=file.filename, status=ExtractionStatus.PARSING)
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    background_tasks.add_task(simulate_llamaparse, extraction.id)

    return extraction


@router.get("/{extraction_id}", response_model=ExtractionRead)
def get_extraction(extraction_id: str, db: Session = Depends(get_db)):
    extraction = db.get(Extraction, extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return extraction


@router.post("/{extraction_id}/extract", response_model=ExtractionRead, status_code=202)
def trigger_extraction(
    extraction_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    extraction = db.get(Extraction, extraction_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    if extraction.status in NOT_READY_FOR_EXTRACT:
        raise HTTPException(
            status_code=409,
            detail=f"Extraction not ready (status={extraction.status.value})",
        )

    extraction.status = ExtractionStatus.EXTRACTING
    extraction.extraction_started_at = datetime.now(UTC)
    db.commit()
    db.refresh(extraction)

    background_tasks.add_task(simulate_vllm_extraction, extraction.id)

    return extraction


@router.get("", response_model=list[ExtractionRead])
def list_extractions(db: Session = Depends(get_db)):
    return db.query(Extraction).order_by(Extraction.created_at.desc()).limit(50).all()
