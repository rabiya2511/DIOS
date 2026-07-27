"""
Pydantic schemas for the Prompt Optimization domain
(Prompt Management APIs blueprint).

Same caveat as prompt_testing.py: everything here is a deterministic,
non-LLM heuristic stub — no real model call rewrites, compresses, expands,
or judges the safety of anything. See router docstring for specifics.
"""

from typing import List, Optional

from pydantic import BaseModel


class PromptOptimizeRequest(BaseModel):
    prompt_id: str
    goal: Optional[str] = None


class PromptOptimizeResponse(BaseModel):
    prompt_id: str
    optimized_content: str
    original_length: int
    optimized_length: int
    reduction_pct: float


class PromptCompressRequest(BaseModel):
    prompt_id: str
    target_ratio: float = 0.5


class PromptCompressResponse(BaseModel):
    prompt_id: str
    compressed_content: str
    original_length: int
    compressed_length: int


class PromptExpandRequest(BaseModel):
    prompt_id: str
    expansion_notes: Optional[str] = None


class PromptExpandResponse(BaseModel):
    prompt_id: str
    expanded_content: str
    original_length: int
    expanded_length: int


class PromptRewriteRequest(BaseModel):
    prompt_id: str
    style: str = "neutral"


class PromptRewriteResponse(BaseModel):
    prompt_id: str
    rewritten_content: str
    style: str


class PromptValidateRequest(BaseModel):
    prompt_id: str


class PromptValidateResponse(BaseModel):
    prompt_id: str
    valid: bool
    issues: List[str]


class PromptSafetyRequest(BaseModel):
    prompt_id: str


class PromptSafetyResponse(BaseModel):
    prompt_id: str
    safe: bool
    flagged_terms: List[str]


class PromptTokenEstimateRequest(BaseModel):
    prompt_id: str


class PromptTokenEstimateResponse(BaseModel):
    prompt_id: str
    character_count: int
    estimated_tokens: int


class PromptLintRequest(BaseModel):
    prompt_id: str


class PromptLintResponse(BaseModel):
    prompt_id: str
    issues: List[str]