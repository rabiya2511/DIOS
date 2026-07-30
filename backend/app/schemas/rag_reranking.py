"""
Pydantic schemas for the Reranking domain (Knowledge / RAG APIs
blueprint).
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel

RelevanceLabel = Literal["high", "medium", "low"]


class RerankItemInput(BaseModel):
    id: str
    content_snippet: str
    score: float = 0.0


class RerankRequest(BaseModel):
    query: str
    results: List[RerankItemInput]


class RerankedItem(BaseModel):
    id: str
    content_snippet: str
    original_score: float
    rerank_score: float


class RerankResponse(BaseModel):
    query: str
    results: List[RerankedItem]


class FusionRequest(BaseModel):
    ranked_lists: List[List[str]]
    k: int = 60


class FusionResultItem(BaseModel):
    doc_id: str
    fused_score: float


class FusionResponse(BaseModel):
    results: List[FusionResultItem]


class ScoreRequest(BaseModel):
    query: str
    content: str


class ScoreResponse(BaseModel):
    query: str
    score: float


class RelevanceRequest(BaseModel):
    query: str
    content: str


class RelevanceResponse(BaseModel):
    query: str
    score: float
    label: RelevanceLabel


class EvaluateRequest(BaseModel):
    retrieved_ids: List[str]
    relevant_ids: List[str]
    k: Optional[int] = None


class EvaluateResponse(BaseModel):
    id: str
    precision: float
    recall: float
    f1: float
    retrieved_count: int
    relevant_count: int
    created_at: datetime


class BenchmarkCase(BaseModel):
    retrieved_ids: List[str]
    relevant_ids: List[str]


class BenchmarkRequest(BaseModel):
    cases: List[BenchmarkCase]


class BenchmarkResponse(BaseModel):
    id: str
    case_count: int
    avg_precision: float
    avg_recall: float
    avg_f1: float
    created_at: datetime


class RagMetricsResponse(BaseModel):
    total_reranks: int
    total_fusions: int
    total_scores: int
    total_relevance_checks: int
    total_evaluations: int
    total_benchmarks: int
    avg_evaluation_f1: float


class RagReportSummary(BaseModel):
    id: str
    type: Literal["evaluate", "benchmark"]
    summary: str
    created_at: datetime