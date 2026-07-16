"""
Policies router — CRUD, test, validate, history, publish, rollback.
Matches the Policies section of the Authorization APIs blueprint (10/10).
Policies live as drafts until explicitly published; publishing snapshots
the current state into policy_versions_db so rollback has something to
revert to.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.policies import (
    PolicyCreateRequest,
    PolicyUpdateRequest,
    PolicyResponse,
    PolicyTestRequest,
    PolicyTestResponse,
    PolicyValidateRequest,
    PolicyValidateResponse,
    PolicyHistoryEntry,
    PolicyPublishRequest,
    PolicyRollbackRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/policies", tags=["Policies"])

# id -> {id, name, description, effect, resource, action, conditions, status, version, created_at, updated_at}
policies_db: dict[str, dict] = {}

# policy id -> list of {version, name, description, effect, resource, action, conditions, published_at}
policy_versions_db: dict[str, list[dict]] = {}

# append-only audit log
policy_history_db: list[dict] = []


def _log_history(policy_id: str, action: str, version: int | None = None):
    policy_history_db.append(
        {
            "policy_id": policy_id,
            "action": action,
            "version": version,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def _get_policy_or_404(id: str) -> dict:
    policy = policies_db.get(id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


def _validate_fields(effect: str, resource: str, action: str) -> list[str]:
    errors = []
    if effect not in ("allow", "deny"):
        errors.append("effect must be 'allow' or 'deny'")
    if not resource or not resource.strip():
        errors.append("resource must not be empty")
    if not action or not action.strip():
        errors.append("action must not be empty")
    return errors


@router.get("", response_model=list[PolicyResponse])
def list_policies():
    return list(policies_db.values())


@router.get("/history", response_model=list[PolicyHistoryEntry])
def get_history():
    return list(policy_history_db)


@router.get("/{id}", response_model=PolicyResponse)
def get_policy(id: str):
    return _get_policy_or_404(id)


@router.post("", response_model=PolicyResponse, status_code=201)
def create_policy(
    data: PolicyCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    errors = _validate_fields(data.effect, data.resource, data.action)
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    policy_id = str(uuid4())
    now = datetime.now(timezone.utc)
    policies_db[policy_id] = {
        "id": policy_id,
        "name": data.name,
        "description": data.description,
        "effect": data.effect,
        "resource": data.resource,
        "action": data.action,
        "conditions": data.conditions,
        "status": "draft",
        "version": 0,
        "created_at": now,
        "updated_at": now,
    }
    policy_versions_db[policy_id] = []
    _log_history(policy_id, "created")
    return policies_db[policy_id]


@router.patch("/{id}", response_model=PolicyResponse)
def update_policy(
    id: str,
    data: PolicyUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    policy = _get_policy_or_404(id)
    for field in ("name", "description", "effect", "resource", "action", "conditions"):
        value = getattr(data, field)
        if value is not None:
            policy[field] = value

    errors = _validate_fields(policy["effect"], policy["resource"], policy["action"])
    if errors:
        raise HTTPException(status_code=422, detail="; ".join(errors))

    # editing a published policy reverts it to draft — must be re-published explicitly
    policy["status"] = "draft"
    policy["updated_at"] = datetime.now(timezone.utc)
    _log_history(id, "updated")
    return policy


@router.delete("/{id}", status_code=204)
def delete_policy(id: str, current_user: dict = Depends(get_current_user)):
    _get_policy_or_404(id)
    del policies_db[id]
    policy_versions_db.pop(id, None)
    _log_history(id, "deleted")
    return None


@router.post("/test", response_model=PolicyTestResponse)
def test_policy(data: PolicyTestRequest):
    # STUB evaluation: an unsaved policy definition tested against a sample request.
    # Matches if resource/action match exactly (or the policy uses "*" wildcard)
    # and every declared condition key/value is present in the request context.
    resource_match = data.resource == "*" or data.resource == data.request_resource
    action_match = data.action == "*" or data.action == data.request_action
    conditions_match = all(
        data.request_context.get(k) == v for k, v in data.conditions.items()
    )

    if resource_match and action_match and conditions_match:
        return PolicyTestResponse(matched=True, effect=data.effect)
    return PolicyTestResponse(matched=False, effect=None)


@router.post("/validate", response_model=PolicyValidateResponse)
def validate_policy(data: PolicyValidateRequest):
    errors = _validate_fields(data.effect, data.resource, data.action)
    return PolicyValidateResponse(valid=len(errors) == 0, errors=errors)


@router.post("/publish", response_model=PolicyResponse)
def publish_policy(
    data: PolicyPublishRequest,
    current_user: dict = Depends(get_current_user),
):
    policy = _get_policy_or_404(data.id)
    new_version = policy["version"] + 1
    now = datetime.now(timezone.utc)

    policy_versions_db.setdefault(data.id, []).append(
        {
            "version": new_version,
            "name": policy["name"],
            "description": policy["description"],
            "effect": policy["effect"],
            "resource": policy["resource"],
            "action": policy["action"],
            "conditions": policy["conditions"],
            "published_at": now,
        }
    )
    policy["version"] = new_version
    policy["status"] = "published"
    policy["updated_at"] = now
    _log_history(data.id, "published", version=new_version)
    return policy


@router.post("/rollback", response_model=PolicyResponse)
def rollback_policy(
    data: PolicyRollbackRequest,
    current_user: dict = Depends(get_current_user),
):
    policy = _get_policy_or_404(data.id)
    versions = policy_versions_db.get(data.id, [])
    snapshot = next((v for v in versions if v["version"] == data.version), None)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Version {data.version} not found for this policy")

    policy["name"] = snapshot["name"]
    policy["description"] = snapshot["description"]
    policy["effect"] = snapshot["effect"]
    policy["resource"] = snapshot["resource"]
    policy["action"] = snapshot["action"]
    policy["conditions"] = snapshot["conditions"]
    policy["status"] = "published"
    policy["updated_at"] = datetime.now(timezone.utc)
    # rollback doesn't create a new version number — it restores an existing one
    policy["version"] = data.version
    _log_history(data.id, "rolled_back", version=data.version)
    return policy