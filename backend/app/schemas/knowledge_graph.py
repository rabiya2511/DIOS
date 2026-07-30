"""
Schemas for the Knowledge Graph group of the Knowledge/RAG APIs
blueprint. Node and edge ids are passed in the request body (not the
URL) for update/delete, matching the blueprint's flat paths
(PATCH/DELETE /graph/node, /graph/edge — no {id} segment).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ---------- Nodes ----------

class GraphNodeCreateRequest(BaseModel):
    label: str = Field(..., description="Node type/category, e.g. 'Person', 'Document'")
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphNodeUpdateRequest(BaseModel):
    node_id: str
    label: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class GraphNodeDeleteRequest(BaseModel):
    node_id: str


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    properties: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------- Edges ----------

class GraphEdgeCreateRequest(BaseModel):
    source_node_id: str
    target_node_id: str
    relationship: str = Field(..., description="Edge type, e.g. 'AUTHORED_BY', 'RELATES_TO'")
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdgeUpdateRequest(BaseModel):
    edge_id: str
    relationship: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None


class GraphEdgeDeleteRequest(BaseModel):
    edge_id: str


class GraphEdgeResponse(BaseModel):
    id: str
    source_node_id: str
    target_node_id: str
    relationship: str
    properties: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------- Query ----------

class GraphQueryResponse(BaseModel):
    nodes: List[GraphNodeResponse]
    edges: List[GraphEdgeResponse]
    total_nodes: int
    total_edges: int


# ---------- Schema ----------

class GraphSchemaResponse(BaseModel):
    node_labels: List[str]
    relationship_types: List[str]
    generated_at: datetime