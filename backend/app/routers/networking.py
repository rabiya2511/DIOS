"""
Networking router — network routes, DNS, certificates.
Matches the Networking section of the Deployment & Infrastructure APIs
blueprint (6/6).

ASSUMPTIONS:
- Platform-wide, not per-user. Any authenticated user can view/modify
  network routes and DNS, and view/renew certificates. Add a role check
  (roles.py/permissions.py exist in this codebase) if this should be
  admin-only in your real deployment — letting any authenticated user
  rewrite DNS or routing is almost certainly too permissive for
  production.
- GET/PATCH /network/routes and GET/PATCH /dns are FULL-REPLACE
  operations, not per-item CRUD — the blueprint gives no {id} path for
  either, so PATCH replaces the entire route table / DNS record set with
  whatever list is sent, rather than upserting individual entries.
- Certificates have NO create endpoint in this blueprint section (only
  GET + renew) — this module SEEDS 2 static demo certificates at import
  time so GET /certificates isn't empty. These are hardcoded example
  data, not real issued certificates. POST /certificates/renew is also a
  STUB: it just extends expires_at by 90 days and flips status to
  "active" — there's no real certificate authority or ACME flow behind
  it.

No route-ordering concerns: /network/routes, /dns, /certificates,
/certificates/renew are all flat, distinct paths with no /{id} catch-alls.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.networking import (
    NetworkRoute,
    NetworkRoutesUpdateRequest,
    NetworkRoutesResponse,
    DnsRecordOut,
    DnsUpdateRequest,
    DnsResponse,
    CertificateOut,
    CertificateRenewRequest,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Networking"])

# Global, platform-wide state (see docstring).
_network_routes: list[dict] = [
    {"destination": "0.0.0.0/0", "target": "internet-gateway", "priority": 100},
]
_network_routes_updated_at = datetime.now(timezone.utc)

_dns_records: dict[str, dict] = {}
_dns_updated_at = datetime.now(timezone.utc)

# --- Seeded demo data (see docstring) — no create endpoint exists for certificates ---
_now = datetime.now(timezone.utc)
certificates_db: dict[str, dict] = {
    "cert-1": {
        "id": "cert-1", "domain": "api.dios.example.com", "issuer": "Let's Encrypt",
        "status": "active", "issued_at": _now - timedelta(days=30), "expires_at": _now + timedelta(days=60),
    },
    "cert-2": {
        "id": "cert-2", "domain": "app.dios.example.com", "issuer": "Let's Encrypt",
        "status": "expiring", "issued_at": _now - timedelta(days=85), "expires_at": _now + timedelta(days=5),
    },
}


@router.get("/network/routes", response_model=NetworkRoutesResponse)
def get_network_routes():
    return NetworkRoutesResponse(
        routes=[NetworkRoute(**r) for r in _network_routes],
        updated_at=_network_routes_updated_at,
    )


@router.patch("/network/routes", response_model=NetworkRoutesResponse)
def update_network_routes(
    data: NetworkRoutesUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    global _network_routes, _network_routes_updated_at
    _network_routes = [r.model_dump() for r in data.routes]
    _network_routes_updated_at = datetime.now(timezone.utc)
    return NetworkRoutesResponse(
        routes=[NetworkRoute(**r) for r in _network_routes],
        updated_at=_network_routes_updated_at,
    )


@router.get("/dns", response_model=DnsResponse)
def get_dns_records():
    return DnsResponse(records=[DnsRecordOut(**r) for r in _dns_records.values()], updated_at=_dns_updated_at)


@router.patch("/dns", response_model=DnsResponse)
def update_dns_records(
    data: DnsUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    global _dns_records, _dns_updated_at
    new_records: dict[str, dict] = {}
    for record in data.records:
        record_id = str(uuid4())
        new_records[record_id] = {
            "id": record_id,
            "domain": record.domain,
            "record_type": record.record_type,
            "value": record.value,
            "ttl": record.ttl,
        }
    _dns_records = new_records
    _dns_updated_at = datetime.now(timezone.utc)
    return DnsResponse(records=[DnsRecordOut(**r) for r in _dns_records.values()], updated_at=_dns_updated_at)


@router.get("/certificates", response_model=list[CertificateOut])
def list_certificates():
    return list(certificates_db.values())


@router.post("/certificates/renew", response_model=CertificateOut)
def renew_certificate(
    data: CertificateRenewRequest,
    current_user: dict = Depends(get_current_user),
):
    cert = certificates_db.get(data.certificate_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    now = datetime.now(timezone.utc)
    cert["issued_at"] = now
    cert["expires_at"] = now + timedelta(days=90)
    cert["status"] = "active"
    return cert