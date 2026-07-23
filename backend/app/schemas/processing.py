"""
Pydantic schemas for the Processing domain (File & Storage APIs
blueprint). STUBBED: no real OCR/compression/encryption pipeline —
each operation synchronously completes and returns a plausible fake
result, but the job record itself is real and retrievable.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

ProcessingOperation = Literal[
    "ocr", "extract_text", "thumbnail", "compress", "encrypt", "decrypt", "virus_scan"
]
JobStatus = Literal["completed", "failed"]


class ProcessingRequest(BaseModel):
    file_id: str


class ProcessingJobResponse(BaseModel):
    id: str
    file_id: str
    operation: ProcessingOperation
    status: JobStatus
    result: dict[str, Any]
    created_at: datetime
    completed_at: datetime | None = None