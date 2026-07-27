"""
Prompt Optimization router — optimize, compress, expand, rewrite, validate,
safety, token-estimate, lint.
Matches the Optimization section of the Prompt Management APIs blueprint
(8/8).

IMPORTANT — READ BEFORE RELYING ON ANY RESULT FROM THIS ROUTER:
Exactly like prompt_testing.py, there is NO real LLM call anywhere here.
Every transformation is a deterministic, rule-based Python heuristic:
- optimize: whitespace collapsing only, not real prompt engineering.
- compress: naive word-boundary truncation to a target ratio.
- expand: string concatenation with a generic filler sentence (or your
  supplied notes) — not genuine elaboration.
- rewrite: a style TAG PREFIX only (e.g. "[Formal] ..."), not an actual
  tone rewrite.
- validate: checks for empty content, unbalanced {} variable braces, and
  an arbitrary length ceiling — not semantic/logical validation.
- safety: substring match against a small, hardcoded list of common
  prompt-injection phrases (e.g. "ignore previous instructions") — a
  best-effort injection-phrase detector, NOT a real content-safety
  classifier. It will miss paraphrased or novel injection attempts and
  says nothing about harmful content in general.
- token-estimate: chars / 4, the common rough English-text approximation
  — not a real tokenizer. Swap in tiktoken or your model provider's
  actual tokenizer before trusting this for billing/context-limit logic.
- lint: checks for trailing whitespace, double spaces, and long lines —
  cosmetic only.

This is enough to exercise the full API contract end-to-end, but NONE of
it should be treated as real prompt engineering, safety moderation, or
token accounting until real logic is wired in.

Operates on prompts_db from prompts.py (Prompt CRUD router) — imported,
not duplicated. Every endpoint requires the caller to own the referenced
prompt, via prompts.py's existing _require_owner.

No route-ordering concerns: every path here is a flat, distinct top-level
name under /api/v1 (/prompt-optimize, /prompt-compress, /prompt-expand,
/prompt-rewrite, /prompt-validate, /prompt-safety, /prompt-token-estimate,
/prompt-lint) — none share a prefix with prompts.router's
/api/v1/prompts/{id}, so nothing can be swallowed by a catch-all.
"""

from fastapi import APIRouter, Depends

from app.schemas.prompt_optimization import (
    PromptOptimizeRequest,
    PromptOptimizeResponse,
    PromptCompressRequest,
    PromptCompressResponse,
    PromptExpandRequest,
    PromptExpandResponse,
    PromptRewriteRequest,
    PromptRewriteResponse,
    PromptValidateRequest,
    PromptValidateResponse,
    PromptSafetyRequest,
    PromptSafetyResponse,
    PromptTokenEstimateRequest,
    PromptTokenEstimateResponse,
    PromptLintRequest,
    PromptLintResponse,
)
from app.routers.prompts import _get_prompt_or_404, _require_owner
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Prompt Optimization"])

# Best-effort, non-exhaustive substring list for the /prompt-safety stub.
# See module docstring — this is a naive detector, not real moderation.
_INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard the system prompt",
    "jailbreak",
    "act as if you have no restrictions",
]


def _owned_prompt(prompt_id: str, current_user: dict) -> dict:
    prompt = _get_prompt_or_404(prompt_id)
    _require_owner(prompt, current_user["email"])
    return prompt


@router.post("/prompt-optimize", response_model=PromptOptimizeResponse)
def optimize_prompt(data: PromptOptimizeRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content = prompt["content"]
    optimized = " ".join(content.split())
    original_len = len(content)
    optimized_len = len(optimized)
    reduction = round((1 - optimized_len / original_len) * 100, 2) if original_len else 0.0
    return PromptOptimizeResponse(
        prompt_id=data.prompt_id, optimized_content=optimized,
        original_length=original_len, optimized_length=optimized_len, reduction_pct=reduction,
    )


@router.post("/prompt-compress", response_model=PromptCompressResponse)
def compress_prompt(data: PromptCompressRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content = prompt["content"]
    target_len = max(1, int(len(content) * data.target_ratio))
    if len(content) <= target_len:
        compressed = content
    else:
        words = content.split()
        out = []
        length = 0
        for w in words:
            if length + len(w) + 1 > target_len:
                break
            out.append(w)
            length += len(w) + 1
        compressed = " ".join(out) + "..."
    return PromptCompressResponse(
        prompt_id=data.prompt_id, compressed_content=compressed,
        original_length=len(content), compressed_length=len(compressed),
    )


@router.post("/prompt-expand", response_model=PromptExpandResponse)
def expand_prompt(data: PromptExpandRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content = prompt["content"]
    addition = data.expansion_notes or (
        "Additional context: this prompt has been expanded with more detail and examples."
    )
    expanded = f"{content}\n\n{addition}"
    return PromptExpandResponse(
        prompt_id=data.prompt_id, expanded_content=expanded,
        original_length=len(content), expanded_length=len(expanded),
    )


@router.post("/prompt-rewrite", response_model=PromptRewriteResponse)
def rewrite_prompt(data: PromptRewriteRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content = prompt["content"]
    rewritten = f"[{data.style.capitalize()}] {content}"
    return PromptRewriteResponse(prompt_id=data.prompt_id, rewritten_content=rewritten, style=data.style)


@router.post("/prompt-validate", response_model=PromptValidateResponse)
def validate_prompt(data: PromptValidateRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content = prompt["content"]
    issues: list[str] = []
    if not content.strip():
        issues.append("Content is empty")
    if content.count("{") != content.count("}"):
        issues.append("Unbalanced curly braces in variable placeholders")
    if len(content) > 5000:
        issues.append("Content exceeds recommended length of 5000 characters")
    return PromptValidateResponse(prompt_id=data.prompt_id, valid=len(issues) == 0, issues=issues)


@router.post("/prompt-safety", response_model=PromptSafetyResponse)
def check_prompt_safety(data: PromptSafetyRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content_lower = prompt["content"].lower()
    flagged = [phrase for phrase in _INJECTION_PHRASES if phrase in content_lower]
    return PromptSafetyResponse(prompt_id=data.prompt_id, safe=len(flagged) == 0, flagged_terms=flagged)


@router.post("/prompt-token-estimate", response_model=PromptTokenEstimateResponse)
def estimate_prompt_tokens(data: PromptTokenEstimateRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content = prompt["content"]
    char_count = len(content)
    estimated_tokens = max(1, round(char_count / 4))
    return PromptTokenEstimateResponse(
        prompt_id=data.prompt_id, character_count=char_count, estimated_tokens=estimated_tokens,
    )


@router.post("/prompt-lint", response_model=PromptLintResponse)
def lint_prompt(data: PromptLintRequest, current_user: dict = Depends(get_current_user)):
    prompt = _owned_prompt(data.prompt_id, current_user)
    content = prompt["content"]
    issues: list[str] = []
    lines = content.splitlines()
    if any(line != line.rstrip() for line in lines):
        issues.append("Trailing whitespace found on one or more lines")
    if "  " in content:
        issues.append("Double spaces found")
    if any(len(line) > 200 for line in lines):
        issues.append("One or more lines exceed 200 characters")
    return PromptLintResponse(prompt_id=data.prompt_id, issues=issues)