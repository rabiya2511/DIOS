"""
Router for the Knowledge Graph group of the Knowledge/RAG APIs
blueprint.
  POST   /api/v1/graph/node
  PATCH  /api/v1/graph/node
  DELETE /api/v1/graph/node
  POST   /api/v1/graph/edge
  PATCH  /api/v1/graph/edge
  DELETE /api/v1/graph/edge
  GET    /api/v1/graph/query
  GET    /api/v1/graph/schema

Node/edge ids are passed in the request body for PATCH/DELETE (no
{id} path segment, matching the blueprint exactly), so there's no
literal-vs-dynamic route ordering concern here — every path is fully
literal. Uses local in-memory dicts (same pattern as conversations_db
in conversations.py).

Deleting a node cascades: any edge referencing it as source or target
is deleted too, to avoid leaving dangling edges pointing at a node
that no longer exists.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.knowledge_graph import (
    GraphNodeCreateRequest,
    GraphNodeUpdateRequest,
    GraphNodeDeleteRequest,
    GraphNodeResponse,
    GraphEdgeCreateRequest,
    GraphEdgeUpdateRequest,
    GraphEdgeDeleteRequest,
    GraphEdgeResponse,
    GraphQueryResponse,
    GraphSchemaResponse,
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/v1/graph", tags=["Knowledge Graph"])

# id -> {id, label, properties, created_at, updated_at}
graph_nodes_db: dict[str, dict] = {}
# id -> {id, source_node_id, target_node_id, relationship, properties, created_at, updated_at}
graph_edges_db: dict[str, dict] = {}


def _get_node_or_404(node_id: str) -> dict:
    node = graph_nodes_db.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node


def _get_edge_or_404(edge_id: str) -> dict:
    edge = graph_edges_db.get(edge_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")
    return edge


# ---------------------------------------------------------------------------
# POST /api/v1/graph/node
# ---------------------------------------------------------------------------
@router.post("/node", response_model=GraphNodeResponse, status_code=201)
def create_node(
    payload: GraphNodeCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new graph node."""
    node_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    node = {
        "id": node_id,
        "label": payload.label,
        "properties": payload.properties,
        "created_at": now,
        "updated_at": now,
    }
    graph_nodes_db[node_id] = node
    return node


# ---------------------------------------------------------------------------
# PATCH /api/v1/graph/node
# ---------------------------------------------------------------------------
@router.patch("/node", response_model=GraphNodeResponse)
def update_node(
    payload: GraphNodeUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing node's label and/or properties."""
    node = _get_node_or_404(payload.node_id)

    if payload.label is not None:
        node["label"] = payload.label
    if payload.properties is not None:
        node["properties"] = payload.properties
    node["updated_at"] = datetime.now(timezone.utc)
    return node


# ---------------------------------------------------------------------------
# DELETE /api/v1/graph/node
# ---------------------------------------------------------------------------
@router.delete("/node", status_code=204)
def delete_node(
    payload: GraphNodeDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Delete a node. Cascades: also deletes any edge referencing it."""
    _get_node_or_404(payload.node_id)

    dangling_edge_ids = [
        edge_id for edge_id, edge in graph_edges_db.items()
        if edge["source_node_id"] == payload.node_id or edge["target_node_id"] == payload.node_id
    ]
    for edge_id in dangling_edge_ids:
        del graph_edges_db[edge_id]

    del graph_nodes_db[payload.node_id]
    return None


# ---------------------------------------------------------------------------
# POST /api/v1/graph/edge
# ---------------------------------------------------------------------------
@router.post("/edge", response_model=GraphEdgeResponse, status_code=201)
def create_edge(
    payload: GraphEdgeCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Create a new edge between two existing nodes."""
    _get_node_or_404(payload.source_node_id)
    _get_node_or_404(payload.target_node_id)

    edge_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    edge = {
        "id": edge_id,
        "source_node_id": payload.source_node_id,
        "target_node_id": payload.target_node_id,
        "relationship": payload.relationship,
        "properties": payload.properties,
        "created_at": now,
        "updated_at": now,
    }
    graph_edges_db[edge_id] = edge
    return edge


# ---------------------------------------------------------------------------
# PATCH /api/v1/graph/edge
# ---------------------------------------------------------------------------
@router.patch("/edge", response_model=GraphEdgeResponse)
def update_edge(
    payload: GraphEdgeUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing edge's relationship type and/or properties."""
    edge = _get_edge_or_404(payload.edge_id)

    if payload.relationship is not None:
        edge["relationship"] = payload.relationship
    if payload.properties is not None:
        edge["properties"] = payload.properties
    edge["updated_at"] = datetime.now(timezone.utc)
    return edge


# ---------------------------------------------------------------------------
# DELETE /api/v1/graph/edge
# ---------------------------------------------------------------------------
@router.delete("/edge", status_code=204)
def delete_edge(
    payload: GraphEdgeDeleteRequest,
    current_user: dict = Depends(get_current_user),
):
    """Delete an edge."""
    _get_edge_or_404(payload.edge_id)
    del graph_edges_db[payload.edge_id]
    return None


# ---------------------------------------------------------------------------
# GET /api/v1/graph/query
# ---------------------------------------------------------------------------
@router.get("/query", response_model=GraphQueryResponse)
def query_graph(
    label: Optional[str] = Query(None, description="Filter nodes by label"),
    relationship: Optional[str] = Query(None, description="Filter edges by relationship type"),
    connected_to: Optional[str] = Query(None, description="Only return edges touching this node_id"),
    current_user: dict = Depends(get_current_user),
):
    """Query nodes and edges in the graph, with optional filters."""
    nodes = list(graph_nodes_db.values())
    if label:
        nodes = [n for n in nodes if n["label"] == label]

    edges = list(graph_edges_db.values())
    if relationship:
        edges = [e for e in edges if e["relationship"] == relationship]
    if connected_to:
        edges = [
            e for e in edges
            if e["source_node_id"] == connected_to or e["target_node_id"] == connected_to
        ]

    return GraphQueryResponse(
        nodes=nodes, edges=edges, total_nodes=len(nodes), total_edges=len(edges),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/graph/schema
# ---------------------------------------------------------------------------
@router.get("/schema", response_model=GraphSchemaResponse)
def get_graph_schema(
    current_user: dict = Depends(get_current_user),
):
    """Return the distinct node labels and relationship types currently in the graph."""
    node_labels = sorted({n["label"] for n in graph_nodes_db.values()})
    relationship_types = sorted({e["relationship"] for e in graph_edges_db.values()})
    return GraphSchemaResponse(
        node_labels=node_labels,
        relationship_types=relationship_types,
        generated_at=datetime.now(timezone.utc),
    )