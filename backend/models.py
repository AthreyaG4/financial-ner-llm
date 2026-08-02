import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, String, Text
from sqlalchemy import Enum as SAEnum

from db import Base


class ExtractionStatus(str, enum.Enum):
    PARSING = "parsing"
    PARSED = "parsed"
    PARSE_FAILED = "parse_failed"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    EXTRACT_FAILED = "extract_failed"


class Extraction(Base):
    __tablename__ = "extractions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = Column(String, nullable=False)
    status = Column(
        SAEnum(
            ExtractionStatus,
            name="extraction_status",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        default=ExtractionStatus.PARSING,
    )

    parsed_text = Column(Text, nullable=True)
    entities = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    parsed_at = Column(DateTime(timezone=True), nullable=True)
    extraction_started_at = Column(DateTime(timezone=True), nullable=True)
    extracted_at = Column(DateTime(timezone=True), nullable=True)
