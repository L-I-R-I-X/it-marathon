"""Main FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.schemas.robinson import RobinsonCruiseRequest
from src.schemas.star import StarVisibilityRequest
from src.schemas.constellation import ConstellationFinderRequest
from src.api.robinson_cruise import process_robinson_cruise
from src.api.star_visibility import process_star_visibility
from src.api.constellation_finder import process_constellation_finder


app = FastAPI(
    title="Digital Marathon 2026 API",
    description="API for processing astronomical and navigation tasks",
    version="1.0.0"
)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Global handler for Pydantic validation errors."""
    return JSONResponse(status_code=400, content={"status": "incorrect_input"})


@app.exception_handler(ValidationError)
async def handle_pydantic_error(request: Request, exc: ValidationError) -> JSONResponse:
    """Handler for raw Pydantic validation errors."""
    return JSONResponse(status_code=400, content={"status": "incorrect_input"})


@app.post("/api/v1/robinson_cruise")
async def robinson_cruise_handler(data: RobinsonCruiseRequest):
    """Handle POST /api/v1/robinson_cruise requests."""
    result = process_robinson_cruise(data.model_dump())
    return result


@app.post("/api/v1/star_visibility")
async def star_visibility_handler(data: StarVisibilityRequest):
    """Handle POST /api/v1/star_visibility requests."""
    result = process_star_visibility(data.model_dump())
    return result


@app.post("/api/v1/constellation_finder")
async def constellation_finder_handler(data: ConstellationFinderRequest):
    """Handle POST /api/v1/constellation_finder requests."""
    result = process_constellation_finder(data.model_dump())
    return result
