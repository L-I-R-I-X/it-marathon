"""Pydantic schemas for star_visibility endpoint validation."""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import List, Optional, Union, Literal, Set
from datetime import datetime


class Vector2D(BaseModel):
    """2D vector coordinates."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    x: Union[float, int]
    y: Union[float, int]


class StarBody(BaseModel):
    """Star celestial body parameters."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    type: Literal["star"]
    id: str
    position: Vector2D
    radius: float = Field(..., gt=0)


class OrbitingBody(BaseModel):
    """Planet or moon celestial body parameters."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    type: Literal["planet", "moon"]
    id: str
    parent_id: str
    orbit_radius: float = Field(..., gt=0)
    angular_velocity: float = Field(..., gt=0)
    initial_angle: float = Field(..., ge=0, lt=360)
    radius: float = Field(..., gt=0)
    rotation_clockwise: bool


class ObservationParams(BaseModel):
    """Observation parameters."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    start_time: datetime
    required_transmission_time: int = Field(..., ge=1, le=1_000_000)
    
    @field_validator('start_time', mode='before')
    @classmethod
    def parse_start_time(cls, v):
        if isinstance(v, str):
            # Handle ISO 8601 format with Z suffix
            if v.endswith('Z'):
                v = v[:-1] + '+00:00'
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                raise ValueError("start_time must be in ISO 8601 format")
        return v


class StarVisibilityRequest(BaseModel):
    """Schema for /api/v1/star_visibility endpoint."""
    model_config = ConfigDict(extra='forbid', coerce_numbers_to_str=False)
    
    target_star_vector: Vector2D
    celestial_bodies: List[Union[StarBody, OrbitingBody]] = Field(default_factory=list)
    observation_params: ObservationParams
    
    @field_validator('celestial_bodies')
    @classmethod
    def check_bodies_limit(cls, v: List[Union[StarBody, OrbitingBody]]) -> List[Union[StarBody, OrbitingBody]]:
        if len(v) > 100:
            raise ValueError("celestial_bodies list cannot exceed 100 items")
        return v
    
    @field_validator('celestial_bodies')
    @classmethod
    def check_bodies_unique_ids(cls, v: List[Union[StarBody, OrbitingBody]]) -> List[Union[StarBody, OrbitingBody]]:
        ids = [body.id for body in v]
        if len(ids) != len(set(ids)):
            raise ValueError("Celestial body ids must be unique")
        return v
    
    @model_validator(mode='after')
    def validate_parent_references(self) -> 'StarVisibilityRequest':
        # Build set of all body ids
        all_ids: Set[str] = {body.id for body in self.celestial_bodies}
        
        # Validate that parent_id references exist
        for body in self.celestial_bodies:
            if body.type in ["planet", "moon"]:
                if body.parent_id not in all_ids:
                    raise ValueError(f"parent_id '{body.parent_id}' does not exist in celestial_bodies")
        
        return self
