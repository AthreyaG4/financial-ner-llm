from datetime import datetime
from typing import Literal

from models import ExtractionStatus
from pydantic import BaseModel, computed_field

EntityType = Literal["monetary", "percentage", "date", "duration", "other_number"]


class EntitySchema(BaseModel):
    value: str
    type: EntityType
    label: str


class ExtractionRead(BaseModel):
    id: str
    file_name: str
    status: ExtractionStatus
    created_at: datetime
    parsed_text: str | None = None
    entities: list[EntitySchema] | None = None
    error_message: str | None = None

    extraction_started_at: datetime | None = None
    extracted_at: datetime | None = None

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def elapsed_label(self) -> str | None:
        if self.extraction_started_at and self.extracted_at:
            secs = (self.extracted_at - self.extraction_started_at).total_seconds()
            return f"{secs:.1f}s"
        return None
