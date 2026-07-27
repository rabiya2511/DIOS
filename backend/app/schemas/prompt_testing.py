"""
Pydantic schemas for the Prompt Testing & Evaluation domain
(Prompt Management APIs blueprint).

All "output"/"score" logic here is STUBBED — there is no real LLM call and
no real quality evaluation. Scores are deterministic placeholder heuristics
(e.g. based on output length) so responses are stable and testable, not
because they reflect real prompt quality. Wire this up to an actual model
call + scoring system before relying on any of it.
"""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel

ResultType = Literal["test", "benchmark", "evaluate", "abtest", "score", "regression"]


class PromptTestRequest(BaseModel):
    prompt_id: str
    input_variables: Dict[str, str] = {}


class PromptTestResult(BaseModel):
    id: str
    prompt_id: str
    type: ResultType = "test"
    output: str
    passed: bool
    latency_ms: float
    created_at: datetime


class PromptBenchmarkCase(BaseModel):
    input: Dict[str, str] = {}
    expected_output: Optional[str] = None


class PromptBenchmarkRequest(BaseModel):
    prompt_id: str
    test_cases: List[PromptBenchmarkCase]


class PromptBenchmarkResult(BaseModel):
    id: str
    prompt_id: str
    type: ResultType = "benchmark"
    total_cases: int
    passed_count: int
    avg_latency_ms: float
    created_at: datetime


class PromptEvaluateRequest(BaseModel):
    prompt_id: str
    output_text: str
    criteria: List[str] = []


class PromptEvaluateResult(BaseModel):
    id: str
    prompt_id: str
    type: ResultType = "evaluate"
    score: float
    feedback: str
    created_at: datetime


class PromptResultSummary(BaseModel):
    id: str
    prompt_id: str
    type: ResultType
    summary: str
    created_at: datetime


class PromptAbTestRequest(BaseModel):
    prompt_id_a: str
    prompt_id_b: str
    test_cases: List[PromptBenchmarkCase]


class PromptAbTestResult(BaseModel):
    id: str
    prompt_id_a: str
    prompt_id_b: str
    type: ResultType = "abtest"
    winner: str
    score_a: float
    score_b: float
    created_at: datetime


class PromptScoreRequest(BaseModel):
    prompt_id: str
    output_text: str


class PromptScoreResult(BaseModel):
    id: str
    prompt_id: str
    type: ResultType = "score"
    score: float
    breakdown: Dict[str, float]
    created_at: datetime


class PromptMetricsResponse(BaseModel):
    total_tests: int
    total_benchmarks: int
    total_evaluations: int
    total_abtests: int
    total_scores: int
    total_regressions: int
    avg_score: float


class PromptRegressionRequest(BaseModel):
    prompt_id: str
    baseline_output: str
    current_output: str


class PromptRegressionResult(BaseModel):
    id: str
    prompt_id: str
    type: ResultType = "regression"
    regression_detected: bool
    similarity: float
    created_at: datetime