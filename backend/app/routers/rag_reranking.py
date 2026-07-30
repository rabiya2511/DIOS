"""
RAG Reranking router — rerank, fusion, score, relevance, metrics,
evaluate, benchmark, reports.
Matches the Reranking section of the Knowledge / RAG APIs blueprint (8/8).

WHAT'S REAL VS. SIMULATED HERE (please read before trusting any of it):
- /rag/fusion implements REAL Reciprocal Rank Fusion (RRF): for each doc
  in each input ranked list, score += 1 / (k + rank). This is a genuine,
  correct, widely-used fusion algorithm — not fabricated.
- /rag/rerank and /rag/score use difflib.SequenceMatcher for text
  similarity between the query and each snippet. This is a REAL string-
  similarity metric (character-sequence overlap), but it is NOT a real
  reranking model / cross-encoder — it's a crude proxy that will not
  capture semantic relevance the way a real reranker would.
- /rag/relevance reuses the same real similarity score and buckets it
  into high/medium/low via a fixed threshold — the bucketing is arbitrary,
  but the underlying score is the same real metric as above.
- /rag/evaluate and /rag/benchmark compute REAL precision/recall/F1 from
  actual set overlap between retrieved_ids and relevant_ids — this is
  standard, correct information-retrieval math.
- IMPORTANT CAVEAT common to all of the above: the ALGORITHMS are real,
  but there is still no real document corpus or retrieval system behind
  any of this (same as rag_retrieval.py / retrieval.py) — you're
  supplying the ranked lists / retrieved IDs / relevant IDs yourself.
  This router computes correctly on whatever you give it; it doesn't
  independently verify relevance against real data.

Every rerank/fusion/score/relevance/evaluate/benchmark call is counted for
GET /rag/metrics, and every evaluate/benchmark result is stored for GET
/rag/reports.

No route-ordering concerns: every path here is a flat, distinct literal
path under /api/v1/rag (rerank, fusion, score, relevance, metrics,
evaluate, benchmark, reports) — none overlap with retrieval.py's endpoint
names (search, retrieve, filter, query, hybrid-search, semantic-search,
keyword-search, history), and there's no /{id} anywhere in either router.
"""

from datetime import datetime, timezone
from difflib import SequenceMatcher
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.schemas.rag_reranking import (
    RerankRequest,
    RerankedItem,
    RerankResponse,
    FusionRequest,
    FusionResultItem,
    FusionResponse,
    ScoreRequest,
    ScoreResponse,
    RelevanceRequest,
    RelevanceResponse,
    EvaluateRequest,
    EvaluateResponse,
    BenchmarkRequest,
    BenchmarkResponse,
    RagMetricsResponse,
    RagReportSummary,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/rag", tags=["RAG Reranking"])

# owner_email -> counters
_counters: dict[str, dict[str, int]] = {}

# owner_email -> [f1 scores from /evaluate calls]
_evaluation_f1_scores: dict[str, list[float]] = {}

# owner_email -> [report dicts], for /evaluate and /benchmark
_reports_db: dict[str, list[dict]] = {}


def _bump(email: str, key: str):
    counters = _counters.setdefault(email, {})
    counters[key] = counters.get(key, 0) + 1


def _similarity(a: str, b: str) -> float:
    """Real string-similarity metric — see module docstring for what it is/isn't."""
    return round(SequenceMatcher(None, a, b).ratio() * 100, 2)


def _precision_recall_f1(retrieved: list[str], relevant: list[str], k: int | None) -> tuple[float, float, float]:
    if k is not None:
        retrieved = retrieved[:k]
    retrieved_set = set(retrieved)
    relevant_set = set(relevant)
    overlap = len(retrieved_set & relevant_set)
    precision = overlap / len(retrieved_set) if retrieved_set else 0.0
    recall = overlap / len(relevant_set) if relevant_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


@router.post("/rerank", response_model=RerankResponse)
def rerank_results(data: RerankRequest, current_user: dict = Depends(get_current_user)):
    reranked = [
        RerankedItem(
            id=item.id,
            content_snippet=item.content_snippet,
            original_score=item.score,
            rerank_score=_similarity(data.query, item.content_snippet),
        )
        for item in data.results
    ]
    reranked.sort(key=lambda r: r.rerank_score, reverse=True)
    _bump(current_user["email"], "reranks")
    return RerankResponse(query=data.query, results=reranked)


@router.post("/fusion", response_model=FusionResponse)
def fuse_ranked_lists(data: FusionRequest, current_user: dict = Depends(get_current_user)):
    # Real Reciprocal Rank Fusion — see module docstring.
    scores: dict[str, float] = {}
    for ranked_list in data.ranked_lists:
        for rank, doc_id in enumerate(ranked_list, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (data.k + rank)
    results = [
        FusionResultItem(doc_id=doc_id, fused_score=round(score, 6))
        for doc_id, score in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    ]
    _bump(current_user["email"], "fusions")
    return FusionResponse(results=results)


@router.post("/score", response_model=ScoreResponse)
def score_passage(data: ScoreRequest, current_user: dict = Depends(get_current_user)):
    score = _similarity(data.query, data.content)
    _bump(current_user["email"], "scores")
    return ScoreResponse(query=data.query, score=score)


@router.post("/relevance", response_model=RelevanceResponse)
def check_relevance(data: RelevanceRequest, current_user: dict = Depends(get_current_user)):
    score = _similarity(data.query, data.content)
    label = "high" if score >= 70 else "medium" if score >= 40 else "low"
    _bump(current_user["email"], "relevance_checks")
    return RelevanceResponse(query=data.query, score=score, label=label)


@router.post("/evaluate", response_model=EvaluateResponse, status_code=201)
def evaluate_retrieval(data: EvaluateRequest, current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    precision, recall, f1 = _precision_recall_f1(data.retrieved_ids, data.relevant_ids, data.k)
    now = datetime.now(timezone.utc)
    report_id = str(uuid4())
    _evaluation_f1_scores.setdefault(email, []).append(f1)
    _reports_db.setdefault(email, []).append({
        "id": report_id, "type": "evaluate",
        "summary": f"precision={precision}, recall={recall}, f1={f1}",
        "created_at": now,
    })
    _bump(email, "evaluations")
    return EvaluateResponse(
        id=report_id, precision=precision, recall=recall, f1=f1,
        retrieved_count=len(data.retrieved_ids), relevant_count=len(data.relevant_ids),
        created_at=now,
    )


@router.post("/benchmark", response_model=BenchmarkResponse, status_code=201)
def benchmark_retrieval(data: BenchmarkRequest, current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    if not data.cases:
        precisions = recalls = f1s = [0.0]
    else:
        results = [_precision_recall_f1(c.retrieved_ids, c.relevant_ids, None) for c in data.cases]
        precisions = [r[0] for r in results]
        recalls = [r[1] for r in results]
        f1s = [r[2] for r in results]

    now = datetime.now(timezone.utc)
    report_id = str(uuid4())
    avg_precision = round(sum(precisions) / len(precisions), 4)
    avg_recall = round(sum(recalls) / len(recalls), 4)
    avg_f1 = round(sum(f1s) / len(f1s), 4)

    _reports_db.setdefault(email, []).append({
        "id": report_id, "type": "benchmark",
        "summary": f"{len(data.cases)} cases, avg_f1={avg_f1}",
        "created_at": now,
    })
    _bump(email, "benchmarks")
    return BenchmarkResponse(
        id=report_id, case_count=len(data.cases),
        avg_precision=avg_precision, avg_recall=avg_recall, avg_f1=avg_f1,
        created_at=now,
    )


@router.get("/metrics", response_model=RagMetricsResponse)
def rag_reranking_metrics(current_user: dict = Depends(get_current_user)):
    email = current_user["email"]
    counters = _counters.get(email, {})
    f1_scores = _evaluation_f1_scores.get(email, [])
    avg_f1 = round(sum(f1_scores) / len(f1_scores), 4) if f1_scores else 0.0
    return RagMetricsResponse(
        total_reranks=counters.get("reranks", 0),
        total_fusions=counters.get("fusions", 0),
        total_scores=counters.get("scores", 0),
        total_relevance_checks=counters.get("relevance_checks", 0),
        total_evaluations=counters.get("evaluations", 0),
        total_benchmarks=counters.get("benchmarks", 0),
        avg_evaluation_f1=avg_f1,
    )


@router.get("/reports", response_model=list[RagReportSummary])
def rag_reranking_reports(current_user: dict = Depends(get_current_user)):
    reports = _reports_db.get(current_user["email"], [])
    reports_sorted = sorted(reports, key=lambda r: r["created_at"], reverse=True)
    return [RagReportSummary(**r) for r in reports_sorted]