"""
Access Evaluation router — check, bulk-check, evaluate, simulate,
effective-permissions, resources, denied, history, cache.
Matches the Access Evaluation section of the Authorization APIs
blueprint (10/10). Ties together Roles, Permissions, Role Assignments,
and Policies into real allow/deny decisions.

Evaluation order: an explicit "deny" policy always wins. Otherwise an
explicit "allow" policy grants access. Otherwise a matching role
permission grants access. Default is deny.
"""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.access import (
    AccessCheckRequest,
    AccessCheckResponse,
    AccessBulkCheckRequest,
    AccessBulkCheckResult,
    AccessBulkCheckResponse,
    MatchedPermission,
    MatchedPolicy,
    AccessEvaluateResponse,
    AccessSimulateRequest,
    AccessSimulateResponse,
    EffectivePermissionsResponse,
    AccessResourcesResponse,
    AccessHistoryEntry,
    AccessCacheEntry,
    AccessCacheResponse,
    AccessCacheClearResponse,
)
from app.models.user import users_db, roles_db
from app.routers.role_assignments import role_assignments_db
from app.routers.permissions import permissions_db
from app.routers.policies import policies_db
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/access", tags=["Access Evaluation"])

# append-only audit log of every check/evaluate call
access_history_db: list[dict] = []

# (user_id, resource, action) -> {allowed, cached_at}
access_cache_db: dict[tuple[str, str, str], dict] = {}


def _find_user_by_id(user_id: str) -> dict:
    for user in users_db.values():
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")


def _user_role_ids(user_id: str) -> list[str]:
    return [a["role_id"] for a in role_assignments_db.values() if a["user_id"] == user_id]


def _permission_matches(permission_key: str, resource: str, action: str) -> bool:
    if permission_key == "*":
        return True
    if permission_key == f"{resource}:{action}":
        return True
    if permission_key == f"{resource}:*":
        return True
    return False


def _policy_matches(policy: dict, resource: str, action: str, context: dict[str, Any]) -> bool:
    if policy["status"] != "published":
        return False
    resource_match = policy["resource"] in (resource, "*")
    action_match = policy["action"] in (action, "*")
    conditions_match = all(context.get(k) == v for k, v in policy["conditions"].items())
    return resource_match and action_match and conditions_match


def _log_history(user_id: str, resource: str, action: str, allowed: bool, reason: str):
    access_history_db.append(
        {
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "allowed": allowed,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc),
        }
    )


def _cache_put(user_id: str, resource: str, action: str, allowed: bool):
    access_cache_db[(user_id, resource, action)] = {
        "allowed": allowed,
        "cached_at": datetime.now(timezone.utc),
    }


def _evaluate(user_id: str, resource: str, action: str, context: dict[str, Any]) -> dict:
    _find_user_by_id(user_id)

    matched_permissions: list[dict] = []
    for role_id in _user_role_ids(user_id):
        role = roles_db.get(role_id)
        if not role:
            continue
        for key in role["permissions"]:
            if _permission_matches(key, resource, action):
                matched_permissions.append(
                    {"role_id": role_id, "role_name": role["name"], "permission_key": key}
                )

    matched_policies: list[dict] = []
    for policy in policies_db.values():
        if _policy_matches(policy, resource, action, context):
            matched_policies.append(
                {"policy_id": policy["id"], "policy_name": policy["name"], "effect": policy["effect"]}
            )

    deny_policy = next((p for p in matched_policies if p["effect"] == "deny"), None)
    if deny_policy:
        allowed, reason = False, f"Denied by policy '{deny_policy['policy_name']}'"
    else:
        allow_policy = next((p for p in matched_policies if p["effect"] == "allow"), None)
        if allow_policy:
            allowed, reason = True, f"Allowed by policy '{allow_policy['policy_name']}'"
        elif matched_permissions:
            mp = matched_permissions[0]
            allowed = True
            reason = f"Allowed by permission '{mp['permission_key']}' via role '{mp['role_name']}'"
        else:
            allowed, reason = False, "No matching permission or policy grants access"

    _log_history(user_id, resource, action, allowed, reason)
    _cache_put(user_id, resource, action, allowed)

    return {
        "allowed": allowed,
        "reason": reason,
        "matched_permissions": matched_permissions,
        "matched_policies": matched_policies,
    }


@router.post("/check", response_model=AccessCheckResponse)
def check_access(data: AccessCheckRequest):
    result = _evaluate(data.user_id, data.resource, data.action, data.context)
    return AccessCheckResponse(allowed=result["allowed"], reason=result["reason"])


@router.post("/bulk-check", response_model=AccessBulkCheckResponse)
def bulk_check_access(data: AccessBulkCheckRequest):
    results = []
    for item in data.checks:
        result = _evaluate(item.user_id, item.resource, item.action, item.context)
        results.append(
            AccessBulkCheckResult(
                user_id=item.user_id,
                resource=item.resource,
                action=item.action,
                allowed=result["allowed"],
                reason=result["reason"],
            )
        )
    return AccessBulkCheckResponse(results=results)


@router.post("/evaluate", response_model=AccessEvaluateResponse)
def evaluate_access(data: AccessCheckRequest):
    result = _evaluate(data.user_id, data.resource, data.action, data.context)
    return AccessEvaluateResponse(
        allowed=result["allowed"],
        reason=result["reason"],
        matched_permissions=[MatchedPermission(**p) for p in result["matched_permissions"]],
        matched_policies=[MatchedPolicy(**p) for p in result["matched_policies"]],
    )


@router.post("/simulate", response_model=AccessSimulateResponse)
def simulate_access(data: AccessSimulateRequest):
    # STUB: hypothetical permissions only — no real user/role/policy lookup,
    # nothing persisted, nothing logged to history/cache.
    matched = any(
        _permission_matches(key, data.resource, data.action) for key in data.hypothetical_permissions
    )
    if matched:
        return AccessSimulateResponse(allowed=True, reason="Allowed by hypothetical permission")
    return AccessSimulateResponse(allowed=False, reason="No hypothetical permission grants access")


@router.get("/effective-permissions", response_model=EffectivePermissionsResponse)
def get_effective_permissions(user_id: str):
    _find_user_by_id(user_id)
    keys: set[str] = set()
    for role_id in _user_role_ids(user_id):
        role = roles_db.get(role_id)
        if role:
            keys.update(role["permissions"])
    return EffectivePermissionsResponse(user_id=user_id, permissions=sorted(keys))


@router.get("/resources", response_model=AccessResourcesResponse)
def get_resources():
    resources: set[str] = set()
    for perm in permissions_db.values():
        resources.add(perm["resource"])
    for policy in policies_db.values():
        if policy["resource"] != "*":
            resources.add(policy["resource"])
    return AccessResourcesResponse(resources=sorted(resources))


@router.get("/denied", response_model=list[AccessHistoryEntry])
def get_denied_history():
    return [entry for entry in access_history_db if not entry["allowed"]]


@router.get("/history", response_model=list[AccessHistoryEntry])
def get_access_history():
    return list(access_history_db)


@router.get("/cache", response_model=AccessCacheResponse)
def get_cache():
    entries = [
        AccessCacheEntry(
            user_id=user_id,
            resource=resource,
            action=action,
            allowed=data["allowed"],
            cached_at=data["cached_at"],
        )
        for (user_id, resource, action), data in access_cache_db.items()
    ]
    return AccessCacheResponse(entries=entries)


@router.delete("/cache", response_model=AccessCacheClearResponse)
def clear_cache(current_user: dict = Depends(get_current_user)):
    count = len(access_cache_db)
    access_cache_db.clear()
    return AccessCacheClearResponse(cleared=count)