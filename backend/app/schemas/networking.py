"""
Pydantic schemas for the Networking domain
(Deployment & Infrastructure APIs blueprint).
"""

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel

CertificateStatus = Literal["active", "expiring", "expired"]


class NetworkRoute(BaseModel):
    destination: str
    target: str
    priority: int = 100


class NetworkRoutesUpdateRequest(BaseModel):
    routes: List[NetworkRoute]


class NetworkRoutesResponse(BaseModel):
    routes: List[NetworkRoute]
    updated_at: datetime


class DnsRecordInput(BaseModel):
    domain: str
    record_type: str = "A"
    value: str
    ttl: int = 3600


class DnsRecordOut(BaseModel):
    id: str
    domain: str
    record_type: str
    value: str
    ttl: int


class DnsUpdateRequest(BaseModel):
    records: List[DnsRecordInput]


class DnsResponse(BaseModel):
    records: List[DnsRecordOut]
    updated_at: datetime


class CertificateOut(BaseModel):
    id: str
    domain: str
    issuer: str
    status: CertificateStatus
    issued_at: datetime
    expires_at: datetime


class CertificateRenewRequest(BaseModel):
    certificate_id: str