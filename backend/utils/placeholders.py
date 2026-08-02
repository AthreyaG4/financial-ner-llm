import time
from datetime import UTC, datetime

from db import SessionLocal
from models import Extraction, ExtractionStatus
from utils.dummy_data import DUMMY_DOCUMENT_TEXT, DUMMY_ENTITIES

PARSE_DELAY_SECONDS = 3.0
EXTRACT_DELAY_SECONDS = 2.5


def simulate_llamaparse(extraction_id: str) -> None:
    """Placeholder for the real LlamaParse call - just waits, then fills in dummy parsed text."""
    time.sleep(PARSE_DELAY_SECONDS)
    db = SessionLocal()
    try:
        extraction = db.get(Extraction, extraction_id)
        if extraction is None:
            return
        extraction.status = ExtractionStatus.PARSED
        extraction.parsed_text = DUMMY_DOCUMENT_TEXT
        extraction.parsed_at = datetime.now(UTC)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - any failure here should mark the row failed
        db.rollback()
        extraction = db.get(Extraction, extraction_id)
        if extraction is not None:
            extraction.status = ExtractionStatus.PARSE_FAILED
            extraction.error_message = str(exc)
            db.commit()
    finally:
        db.close()


def simulate_vllm_extraction(extraction_id: str) -> None:
    """Placeholder for the real vLLM entity-extraction call - just waits, then fills in dummy entities."""
    time.sleep(EXTRACT_DELAY_SECONDS)
    db = SessionLocal()
    try:
        extraction = db.get(Extraction, extraction_id)
        if extraction is None:
            return
        extraction.status = ExtractionStatus.EXTRACTED
        extraction.entities = DUMMY_ENTITIES
        extraction.extracted_at = datetime.now(UTC)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - any failure here should mark the row failed
        db.rollback()
        extraction = db.get(Extraction, extraction_id)
        if extraction is not None:
            extraction.status = ExtractionStatus.EXTRACT_FAILED
            extraction.error_message = str(exc)
            db.commit()
    finally:
        db.close()
