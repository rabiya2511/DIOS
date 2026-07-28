"""
Containers & Images router — containers list, build/push/scan images,
delete images.
Matches the Containers & Images section of the Deployment &
Infrastructure APIs blueprint (6/6).

ASSUMPTIONS:
- GET /containers has NO create endpoint anywhere in this blueprint
  section — there's no "run a container" API. To avoid it being
  permanently empty, this module SEEDS a small set of static demo running
  containers at import time (see containers_db below). These are hardcoded
  example data, not real running containers — replace with a real
  container runtime/orchestrator query when this needs to be real.
- Images, by contrast, ARE genuinely created/managed through this API:
  POST /containers/build creates a new image record; POST
  /containers/push marks it pushed to a registry; POST /images/scan
  attaches a (stubbed) vulnerability result; DELETE /images/{id} removes
  it. Only the user who built an image can push, scan, or delete it.
- POST /images/scan is a DETERMINISTIC STUB, not a real vulnerability
  scanner: it flags a placeholder CVE based on the image name's length
  purely so the endpoint has varied, reproducible output. It says nothing
  about the actual security of any real image. Wire in a real scanner
  (e.g. Trivy, Grype) before trusting this for anything.

No route-ordering concerns: /containers, /containers/build,
/containers/push are distinct literal paths; /images ("" and /scan) are
under one prefix with /{id} only used for DELETE — but since /scan is a
POST and /{id} is only registered for DELETE, there's no method+path
overlap to worry about (see prompt_members.py precedent for why
different-method routes on similar-looking paths don't conflict). Still,
/scan is registered before /{id} here as a defensive convention, matching
the rest of this codebase.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.containers import (
    ContainerOut,
    ImageBuildRequest,
    ImagePushRequest,
    ImageScanRequest,
    ImageOut,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1", tags=["Containers & Images"])

# --- Seeded demo data (see docstring) — no create endpoint exists for containers ---
containers_db: dict[str, dict] = {
    "ctr-1": {"id": "ctr-1", "name": "auth-service-0", "image": "dios/auth-service:1.2.0", "status": "running", "cluster_id": None},
    "ctr-2": {"id": "ctr-2", "name": "billing-service-0", "image": "dios/billing-service:2.0.1", "status": "running", "cluster_id": None},
    "ctr-3": {"id": "ctr-3", "name": "worker-queue-0", "image": "dios/worker:0.9.4", "status": "crashed", "cluster_id": None},
}

# id -> {id, name, tag, size_mb, status, pushed_to_registry, registry, vulnerabilities, last_scanned_at, built_by, created_at}
images_db: dict[str, dict] = {}


def _get_image_or_404(id: str) -> dict:
    image = images_db.get(id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    return image


def _require_builder(image: dict, email: str):
    if image["built_by"] != email:
        raise HTTPException(status_code=403, detail="Only the user who built this image can perform this action")


@router.get("/containers", response_model=list[ContainerOut])
def list_containers():
    return list(containers_db.values())


@router.post("/containers/build", response_model=ImageOut, status_code=201)
def build_image(data: ImageBuildRequest, current_user: dict = Depends(get_current_user)):
    image_id = str(uuid4())
    now = datetime.now(timezone.utc)
    # Deterministic stub size, purely for varied/reproducible output.
    size_mb = 50 + (len(data.name) * 7) % 400
    images_db[image_id] = {
        "id": image_id,
        "name": data.name,
        "tag": data.tag,
        "size_mb": size_mb,
        "status": "built",
        "pushed_to_registry": False,
        "registry": None,
        "vulnerabilities": None,
        "last_scanned_at": None,
        "built_by": current_user["email"],
        "created_at": now,
    }
    return images_db[image_id]


@router.post("/containers/push", response_model=ImageOut)
def push_image(data: ImagePushRequest, current_user: dict = Depends(get_current_user)):
    image = _get_image_or_404(data.image_id)
    _require_builder(image, current_user["email"])
    image["status"] = "pushed"
    image["pushed_to_registry"] = True
    image["registry"] = data.registry
    return image


@router.get("/images", response_model=list[ImageOut])
def list_images():
    return list(images_db.values())


@router.post("/images/scan", response_model=ImageOut)
def scan_image(data: ImageScanRequest, current_user: dict = Depends(get_current_user)):
    image = _get_image_or_404(data.image_id)
    _require_builder(image, current_user["email"])
    # STUB — see module docstring. Deterministic, not a real scanner.
    if len(image["name"]) % 3 == 0:
        vulnerabilities = []
    else:
        vulnerabilities = ["CVE-2024-EXAMPLE-1234 (stub, low severity, not a real finding)"]
    image["vulnerabilities"] = vulnerabilities
    image["last_scanned_at"] = datetime.now(timezone.utc)
    return image


@router.delete("/images/{id}", status_code=204)
def delete_image(id: str, current_user: dict = Depends(get_current_user)):
    image = _get_image_or_404(id)
    _require_builder(image, current_user["email"])
    del images_db[id]
    return None