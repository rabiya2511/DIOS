"""
Processing router — ocr, extract-text, thumbnail, compress, encrypt,
decrypt, virus-scan, jobs. Matches the Processing section of the
File & Storage APIs blueprint (8/8). STUBBED: each operation
synchronously "completes" and returns a plausible fake result; only
the file owner can run operations on their own files.
"""

import random
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.processing import ProcessingRequest, ProcessingJobResponse
from app.routers.fileslifecycle import files_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/processing", tags=["Processing"])

# id -> {id, file_id, operation, status, result, created_at, completed_at}
processing_jobs_db: dict[str, dict] = {}


def _get_owned_file(file_id: str, email: str) -> dict:
    file = files_db.get(file_id)
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if file["owner_email"] != email:
        raise HTTPException(status_code=403, detail="Only the file owner can perform this action")
    return file


def _run_job(file: dict, operation: str, result: dict) -> dict:
    job_id = str(uuid4())
    now = datetime.now(timezone.utc)
    job = {
        "id": job_id,
        "file_id": file["id"],
        "operation": operation,
        "status": "completed",
        "result": result,
        "created_at": now,
        "completed_at": now,
    }
    processing_jobs_db[job_id] = job
    return job


@router.post("/ocr", response_model=ProcessingJobResponse)
def run_ocr(data: ProcessingRequest, current_user: dict = Depends(get_current_user)):
    file = _get_owned_file(data.file_id, current_user["email"])
    return _run_job(file, "ocr", {"extracted_text": f"Sample OCR text extracted from {file['name']}"})


@router.post("/extract-text", response_model=ProcessingJobResponse)
def extract_text(data: ProcessingRequest, current_user: dict = Depends(get_current_user)):
    file = _get_owned_file(data.file_id, current_user["email"])
    return _run_job(
        file, "extract_text", {"extracted_text": f"Sample plain text extracted from {file['name']}"}
    )


@router.post("/thumbnail", response_model=ProcessingJobResponse)
def generate_thumbnail(data: ProcessingRequest, current_user: dict = Depends(get_current_user)):
    file = _get_owned_file(data.file_id, current_user["email"])
    return _run_job(
        file, "thumbnail", {"thumbnail_url": f"https://cdn.example.com/thumbnails/{file['id']}.jpg"}
    )


@router.post("/compress", response_model=ProcessingJobResponse)
def compress_file(data: ProcessingRequest, current_user: dict = Depends(get_current_user)):
    file = _get_owned_file(data.file_id, current_user["email"])
    original = file.get("size_bytes", 1000)
    compressed = round(original * 0.6)
    return _run_job(
        file,
        "compress",
        {
            "original_size_bytes": original,
            "compressed_size_bytes": compressed,
            "ratio": round(compressed / original, 2) if original else 0,
        },
    )


@router.post("/encrypt", response_model=ProcessingJobResponse)
def encrypt_file(data: ProcessingRequest, current_user: dict = Depends(get_current_user)):
    file = _get_owned_file(data.file_id, current_user["email"])
    return _run_job(file, "encrypt", {"encrypted": True, "key_id": str(uuid4())})


@router.post("/decrypt", response_model=ProcessingJobResponse)
def decrypt_file(data: ProcessingRequest, current_user: dict = Depends(get_current_user)):
    file = _get_owned_file(data.file_id, current_user["email"])
    return _run_job(file, "decrypt", {"decrypted": True})


@router.post("/virus-scan", response_model=ProcessingJobResponse)
def virus_scan(data: ProcessingRequest, current_user: dict = Depends(get_current_user)):
    file = _get_owned_file(data.file_id, current_user["email"])
    return _run_job(file, "virus_scan", {"clean": True, "threats_found": []})


@router.get("/jobs", response_model=list[ProcessingJobResponse])
def list_jobs(current_user: dict = Depends(get_current_user)):
    owned_file_ids = {
        f["id"] for f in files_db.values() if f["owner_email"] == current_user["email"]
    }
    return [j for j in processing_jobs_db.values() if j["file_id"] in owned_file_ids]