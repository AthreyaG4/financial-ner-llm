from datetime import UTC, datetime, timedelta

from models import ExtractionStatus
from schemas import ExtractionRead


def test_elapsed_label_none_without_timestamps():
    read = ExtractionRead(
        id="x",
        file_name="f.pdf",
        status=ExtractionStatus.PARSING,
        created_at=datetime.now(UTC),
    )
    assert read.elapsed_label is None


def test_elapsed_label_computed_from_timestamps():
    start = datetime.now(UTC)
    end = start + timedelta(seconds=2, milliseconds=500)
    read = ExtractionRead(
        id="x",
        file_name="f.pdf",
        status=ExtractionStatus.EXTRACTED,
        created_at=start,
        extraction_started_at=start,
        extracted_at=end,
    )
    assert read.elapsed_label == "2.5s"
