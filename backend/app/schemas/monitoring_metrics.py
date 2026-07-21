"""
Pydantic schemas for the Metrics domain (Monitoring APIs blueprint).
Real system stats via psutil (CPU, memory, disk, network) — not stubbed.
"""

from pydantic import BaseModel


class CpuMetrics(BaseModel):
    percent: float
    core_count: int


class MemoryMetrics(BaseModel):
    total_mb: float
    used_mb: float
    percent: float


class StorageMetrics(BaseModel):
    total_gb: float
    used_gb: float
    percent: float


class NetworkMetrics(BaseModel):
    bytes_sent: int
    bytes_recv: int


class MetricsResponse(BaseModel):
    cpu: CpuMetrics
    memory: MemoryMetrics
    storage: StorageMetrics
    network: NetworkMetrics