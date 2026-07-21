"""
Metrics router — cpu, memory, storage, network, combined metrics.
Matches the Metrics section of the Monitoring APIs blueprint (5/5).
Uses psutil for real system stats (not stubbed).
"""

import psutil
from fastapi import APIRouter

from app.schemas.monitoring_metrics import (
    CpuMetrics,
    MemoryMetrics,
    StorageMetrics,
    NetworkMetrics,
    MetricsResponse,
)

router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring Metrics"])


def _get_cpu() -> CpuMetrics:
    return CpuMetrics(percent=psutil.cpu_percent(interval=0.1), core_count=psutil.cpu_count() or 1)


def _get_memory() -> MemoryMetrics:
    vm = psutil.virtual_memory()
    return MemoryMetrics(
        total_mb=round(vm.total / (1024 * 1024), 2),
        used_mb=round(vm.used / (1024 * 1024), 2),
        percent=vm.percent,
    )


def _get_storage() -> StorageMetrics:
    du = psutil.disk_usage("/")
    return StorageMetrics(
        total_gb=round(du.total / (1024 ** 3), 2),
        used_gb=round(du.used / (1024 ** 3), 2),
        percent=du.percent,
    )


def _get_network() -> NetworkMetrics:
    net = psutil.net_io_counters()
    return NetworkMetrics(bytes_sent=net.bytes_sent, bytes_recv=net.bytes_recv)


@router.get("/metrics", response_model=MetricsResponse)
def get_metrics():
    return MetricsResponse(
        cpu=_get_cpu(), memory=_get_memory(), storage=_get_storage(), network=_get_network()
    )


@router.get("/cpu", response_model=CpuMetrics)
def get_cpu():
    return _get_cpu()


@router.get("/memory", response_model=MemoryMetrics)
def get_memory():
    return _get_memory()


@router.get("/storage", response_model=StorageMetrics)
def get_storage():
    return _get_storage()


@router.get("/network", response_model=NetworkMetrics)
def get_network():
    return _get_network()