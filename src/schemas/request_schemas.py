"""Pydantic schemas for request validation."""

from pydantic import BaseModel, Field
from typing import Optional, List


class RobinsonCruiseRequest(BaseModel):
    """Schema for /api/v1/robinson_cruise endpoint."""
    # TODO: Add actual fields based on task specification
    # Placeholder - will be updated with real schema
    pass


class StarVisibilityRequest(BaseModel):
    """Schema for /api/v1/star_visibility endpoint."""
    # TODO: Add actual fields based on task specification
    # Placeholder - will be updated with real schema
    pass


class ConstellationFinderRequest(BaseModel):
    """Schema for /api/v1/constellation_finder endpoint."""
    # TODO: Add actual fields based on task specification
    # Placeholder - will be updated with real schema
    pass
