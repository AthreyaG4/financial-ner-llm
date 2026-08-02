from models import Extraction, ExtractionStatus
from utils import placeholders


def _make_extraction(db_session, status):
    extraction = Extraction(file_name="test.pdf", status=status)
    db_session.add(extraction)
    db_session.commit()
    db_session.refresh(extraction)
    return extraction


def _use_test_session(monkeypatch, db_session):
    # placeholders open their own SessionLocal() - point that at the test DB,
    # and stop the placeholder's `finally: db.close()` from closing the shared test session.
    monkeypatch.setattr(placeholders, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(db_session, "close", lambda: None)


def test_simulate_llamaparse_marks_parsed(db_session, monkeypatch):
    monkeypatch.setattr(placeholders, "PARSE_DELAY_SECONDS", 0)
    _use_test_session(monkeypatch, db_session)

    extraction = _make_extraction(db_session, ExtractionStatus.PARSING)
    placeholders.simulate_llamaparse(extraction.id)

    db_session.refresh(extraction)
    assert extraction.status == ExtractionStatus.PARSED
    assert extraction.parsed_text
    assert extraction.parsed_at is not None


def test_simulate_vllm_extraction_marks_extracted(db_session, monkeypatch):
    monkeypatch.setattr(placeholders, "EXTRACT_DELAY_SECONDS", 0)
    _use_test_session(monkeypatch, db_session)

    extraction = _make_extraction(db_session, ExtractionStatus.EXTRACTING)
    placeholders.simulate_vllm_extraction(extraction.id)

    db_session.refresh(extraction)
    assert extraction.status == ExtractionStatus.EXTRACTED
    assert extraction.entities
    assert extraction.extracted_at is not None
