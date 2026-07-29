"""
Pydantic schemas for the AI Chat: Multimodal domain.
All processing is STUBBED — no real vision/audio/OCR pipeline exists yet.
"""

from typing import Optional

from pydantic import BaseModel


class ImageRequest(BaseModel):
    chat_id: str
    image_url: str
    prompt: Optional[str] = None


class ImageResponse(BaseModel):
    description: str
    tags: list[str]


class VisionRequest(BaseModel):
    chat_id: str
    image_url: str
    question: str


class VisionResponse(BaseModel):
    answer: str
    confidence: float


class AudioRequest(BaseModel):
    chat_id: str
    audio_url: str


class AudioResponse(BaseModel):
    transcript: str
    duration_seconds: float


class VideoRequest(BaseModel):
    chat_id: str
    video_url: str


class VideoResponse(BaseModel):
    summary: str
    duration_seconds: float
    frame_count: int


class DocumentRequest(BaseModel):
    chat_id: str
    document_url: str


class DocumentResponse(BaseModel):
    extracted_text: str
    page_count: int


class PdfRequest(BaseModel):
    chat_id: str
    pdf_url: str


class PdfResponse(BaseModel):
    extracted_text: str
    page_count: int


class OcrRequest(BaseModel):
    image_url: str


class OcrResponse(BaseModel):
    text: str
    confidence: float


class SpeechToTextRequest(BaseModel):
    audio_url: str
    language: str = "en"


class SpeechToTextResponse(BaseModel):
    transcript: str
    language: str


class TextToSpeechRequest(BaseModel):
    text: str
    voice: str = "default"


class TextToSpeechResponse(BaseModel):
    audio_url: str
    duration_seconds: float


class TranslateRequest(BaseModel):
    text: str
    target_language: str


class TranslateResponse(BaseModel):
    translated_text: str
    source_language: str
    target_language: str
    