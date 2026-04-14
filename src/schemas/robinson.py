"""Pydantic schemas for robinson_cruise endpoint validation."""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Optional, Set
from datetime import timedelta


class GravityAssist(BaseModel):
    """Gravity assist maneuver parameters."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    velocity_gain: float = Field(..., ge=0)
    fuel_consumption: int = Field(..., ge=0)
    time_to_execute: int = Field(..., ge=0)


class Body(BaseModel):
    """Celestial body with gravity assists."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    id: str
    gravity_assists: List[GravityAssist] = Field(default_factory=list)
    
    @field_validator('id')
    @classmethod
    def check_id_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Body id cannot be empty")
        return v


class Edge(BaseModel):
    """Edge between two celestial bodies."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False, populate_by_name=True)
    
    from_: str = Field(..., alias='from')
    to: str
    distance: float = Field(..., gt=0)
    
    @field_validator('from_', 'to')
    @classmethod
    def check_node_not_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Node id cannot be empty")
        return v


class RobinsonCruiseRequest(BaseModel):
    """Schema for /api/v1/robinson_cruise endpoint."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    mass_shuttle: float = Field(..., gt=0)
    mass_fuel_unit: float = Field(..., gt=0)
    power_per_unit: float = Field(..., gt=0)
    oxygen_time: int = Field(..., ge=0)
    total_fuel: int = Field(..., ge=0)
    fuel_consumption: float = Field(..., gt=0)
    bodies: List[Body] = Field(default_factory=list)
    edges: List[Edge]
    
    @field_validator('bodies')
    @classmethod
    def check_bodies_limit(cls, v: List[Body]) -> List[Body]:
        if len(v) > 100:
            raise ValueError("bodies list cannot exceed 100 items")
        return v
    
    @field_validator('bodies')
    @classmethod
    def check_bodies_unique_ids(cls, v: List[Body]) -> List[Body]:
        ids = [body.id for body in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Body ids must be unique")
        return v
    
    @field_validator('edges')
    @classmethod
    def check_edges_non_empty(cls, v: List[Edge]) -> List[Edge]:
        if len(v) == 0:
            raise ValueError("edges list cannot be empty")
        return v
    
    @model_validator(mode='after')
    def validate_graph_structure(self) -> 'RobinsonCruiseRequest':
        # Check that start_point and rescue_point are present in edges
        all_nodes: Set[str] = set()
        for edge in self.edges:
            all_nodes.add(edge.from_)
            all_nodes.add(edge.to)
        
        if 'start_point' not in all_nodes:
            raise ValueError("edges must contain 'start_point'")
        if 'rescue_point' not in all_nodes:
            raise ValueError("edges must contain 'rescue_point'")
        
        # Check that all nodes referenced in edges exist in bodies (except start_point and rescue_point)
        body_ids: Set[str] = {body.id for body in self.bodies}
        for edge in self.edges:
            for node in [edge.from_, edge.to]:
                if node not in ['start_point', 'rescue_point'] and node not in body_ids:
                    raise ValueError(f"Edge references unknown body '{node}' not in bodies")
        
        return self
