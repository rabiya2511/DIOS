"""
Infrastructure router — clusters, nodes, services, load balancers, storage.
Matches the Infrastructure section of the Deployment & Infrastructure
APIs blueprint (6/6).

ASSUMPTIONS:
- This is platform-wide infrastructure visibility, not per-user ownership.
  Any authenticated user can GET clusters/nodes/services/load-balancers/
  storage. POST /infrastructure/clusters records who created the cluster
  (created_by) but doesn't restrict who can view it afterward. Add a role
  check (this codebase has roles.py/permissions.py) if infra visibility
  should be admin-only in your real deployment.
- Nodes are auto-generated when a cluster is created: POST
  /infrastructure/clusters with node_count=N creates N corresponding node
  records in nodes_db. There's no standalone "create node" endpoint in
  this blueprint section, so nodes only exist as a side effect of cluster
  creation.
- services, load-balancers, and storage have NO create endpoints in this
  blueprint section (only GET) — there is no real orchestration behind
  them. To keep GET /services, GET /load-balancers, and GET /storage from
  being permanently empty, this module SEEDS a small set of static demo
  entries at import time. These are hardcoded example data, not
  real infrastructure — clearly not meant to reflect your actual
  deployment. Replace with a real data source (e.g. a Kubernetes API
  client, cloud provider SDK) when this needs to be real.

No route-ordering concerns: /nodes, /services, /load-balancers, /storage
are flat top-level paths; /infrastructure/clusters is a distinct nested
prefix with only "" GET/POST (no /{id} catch-all here to collide with).
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query

from app.schemas.infrastructure import (
    ClusterCreateRequest,
    ClusterOut,
    NodeOut,
    ServiceOut,
    LoadBalancerOut,
    StorageVolumeOut,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Infrastructure"])

# id -> {id, name, region, status, node_count, created_by, created_at}
clusters_db: dict[str, dict] = {}

# id -> {id, cluster_id, name, status, cpu_cores, memory_gb}
nodes_db: dict[str, dict] = {}

# --- Seeded demo data (see docstring) — no create endpoint exists for these ---
services_db: dict[str, dict] = {
    "svc-1": {"id": "svc-1", "name": "auth-service", "status": "healthy", "replicas": 3, "cluster_id": None},
    "svc-2": {"id": "svc-2", "name": "billing-service", "status": "healthy", "replicas": 2, "cluster_id": None},
    "svc-3": {"id": "svc-3", "name": "notification-service", "status": "degraded", "replicas": 1, "cluster_id": None},
}

load_balancers_db: dict[str, dict] = {
    "lb-1": {"id": "lb-1", "name": "public-lb", "status": "active", "region": "us-east-1", "target_service": "auth-service"},
    "lb-2": {"id": "lb-2", "name": "internal-lb", "status": "active", "region": "us-east-1", "target_service": "billing-service"},
}

storage_volumes_db: dict[str, dict] = {
    "vol-1": {"id": "vol-1", "name": "primary-db-volume", "size_gb": 500, "region": "us-east-1", "attached_to": "auth-service"},
    "vol-2": {"id": "vol-2", "name": "backup-volume", "size_gb": 1000, "region": "us-east-1", "attached_to": None},
}


@router.get("/infrastructure/clusters", response_model=list[ClusterOut])
def list_clusters():
    return list(clusters_db.values())


@router.post("/infrastructure/clusters", response_model=ClusterOut, status_code=201)
def create_cluster(
    data: ClusterCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    cluster_id = str(uuid4())
    now = datetime.now(timezone.utc)
    clusters_db[cluster_id] = {
        "id": cluster_id,
        "name": data.name,
        "region": data.region,
        "status": "provisioning",
        "node_count": data.node_count,
        "created_by": current_user["email"],
        "created_at": now,
    }
    for i in range(data.node_count):
        node_id = str(uuid4())
        nodes_db[node_id] = {
            "id": node_id,
            "cluster_id": cluster_id,
            "name": f"{data.name}-node-{i + 1}",
            "status": "ready",
            "cpu_cores": 4,
            "memory_gb": 16,
        }
    clusters_db[cluster_id]["status"] = "active"
    return clusters_db[cluster_id]


@router.get("/nodes", response_model=list[NodeOut])
def list_nodes(cluster_id: str | None = Query(default=None)):
    nodes = list(nodes_db.values())
    if cluster_id is not None:
        nodes = [n for n in nodes if n["cluster_id"] == cluster_id]
    return nodes


@router.get("/services", response_model=list[ServiceOut])
def list_services():
    return list(services_db.values())


@router.get("/load-balancers", response_model=list[LoadBalancerOut])
def list_load_balancers():
    return list(load_balancers_db.values())


@router.get("/storage", response_model=list[StorageVolumeOut])
def list_storage_volumes():
    return list(storage_volumes_db.values())