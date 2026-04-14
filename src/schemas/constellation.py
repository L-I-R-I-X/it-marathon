"""Pydantic schemas for constellation_finder endpoint validation."""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Set


class Star(BaseModel):
    """Star with 3D coordinates."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    name: str
    x: float
    y: float
    z: float
    
    @field_validator('name')
    @classmethod
    def check_name_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Star name cannot be empty")
        return v


class ClusterParams(BaseModel):
    """Clustering parameters."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    min_size: int = Field(..., ge=1)
    max_size: int = Field(..., ge=1)
    max_neighbor_distance: float = Field(..., gt=0)
    
    @model_validator(mode='after')
    def validate_size_range(self) -> 'ClusterParams':
        if self.max_size < self.min_size:
            raise ValueError("max_size must be >= min_size")
        return self


class TargetEdge(BaseModel):
    """Edge in target constellation graph."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    from_: int = Field(..., alias='from', ge=0)
    to: int = Field(..., ge=0)
    distance: float = Field(..., gt=0)


class TargetConstellation(BaseModel):
    """Target constellation graph structure."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    edges: List[TargetEdge]


class ConstellationFinderRequest(BaseModel):
    """Schema for /api/v1/constellation_finder endpoint."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    stars: List[Star] = Field(default_factory=list)
    cluster_params: ClusterParams
    target_constellation: TargetConstellation
    
    @field_validator('stars')
    @classmethod
    def check_stars_limit(cls, v: List[Star]) -> List[Star]:
        if len(v) > 1000:
            raise ValueError("stars list cannot exceed 1000 items")
        return v
    
    @field_validator('stars')
    @classmethod
    def check_stars_unique_names(cls, v: List[Star]) -> List[Star]:
        names = [star.name for star in v]
        if len(names) != len(set(names)):
            raise ValueError("Star names must be unique")
        return v
    
    @model_validator(mode='after')
    def validate_target_constellation(self) -> 'ConstellationFinderRequest':
        edges = self.target_constellation.edges
        
        if len(edges) == 0:
            raise ValueError("target_constellation edges cannot be empty")
        
        # Collect all vertices referenced in edges
        vertices: Set[int] = set()
        for edge in edges:
            vertices.add(edge.from_)
            vertices.add(edge.to)
        
        if len(vertices) < 2:
            raise ValueError("target_constellation must have at least 2 vertices")
        
        # Check that vertices are [0, n-1] without gaps
        n = len(vertices)
        expected_vertices = set(range(n))
        if vertices != expected_vertices:
            raise ValueError(f"target_constellation vertices must be [0, {n-1}] without gaps")
        
        # Check tree properties: n vertices, n-1 edges
        if len(edges) != n - 1:
            raise ValueError(f"target_constellation must have exactly {n-1} edges for {n} vertices (tree property)")
        
        # Check for self-loops and multiple edges
        edge_set: Set[tuple] = set()
        for edge in edges:
            # Check for self-loop
            if edge.from_ == edge.to:
                raise ValueError("target_constellation cannot have self-loops")
            
            # Normalize edge for undirected comparison
            normalized = tuple(sorted([edge.from_, edge.to]))
            if normalized in edge_set:
                raise ValueError("target_constellation cannot have multiple edges between same vertices")
            edge_set.add(normalized)
        
        # Check connectivity using Union-Find
        parent = list(range(n))
        
        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x: int, y: int) -> bool:
            px, py = find(x), find(y)
            if px == py:
                return False  # Already connected - would create cycle
            parent[px] = py
            return True
        
        for edge in edges:
            if not union(edge.from_, edge.to):
                raise ValueError("target_constellation contains a cycle (not a tree)")
        
        # Check that all vertices are connected (no isolated vertices)
        root = find(0)
        for i in range(1, n):
            if find(i) != root:
                raise ValueError("target_constellation is not connected")
        
        return self
