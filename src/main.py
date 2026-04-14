"""Main FastAPI application entry point."""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from src.validators.input_validator import validate_input
from src.api.robinson_cruise import process_robinson_cruise
from src.api.star_visibility import process_star_visibility
from src.api.constellation_finder import process_constellation_finder


app = FastAPI(
    title="Digital Marathon 2026 API",
    description="API for processing astronomical and navigation tasks",
    version="1.0.0"
)


@app.post("/api/v1/robinson_cruise")
async def robinson_cruise_handler(request: Request):
    """Handle POST /api/v1/robinson_cruise requests."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"status": "incorrect_input"})
    
    try:
        validate_input("robinson_cruise", data)
    except (ValueError, AssertionError):
        return JSONResponse(status_code=400, content={"status": "incorrect_input"})
    
    result = process_robinson_cruise(data)
    return result


@app.post("/api/v1/star_visibility")
async def star_visibility_handler(request: Request):
    """Handle POST /api/v1/star_visibility requests."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"status": "incorrect_input"})
    
    try:
        validate_input("star_visibility", data)
    except (ValueError, AssertionError):
        return JSONResponse(status_code=400, content={"status": "incorrect_input"})
    
    result = process_star_visibility(data)
    return result


@app.post("/api/v1/constellation_finder")
async def constellation_finder_handler(request: Request):
    """Handle POST /api/v1/constellation_finder requests."""
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail={"status": "incorrect_input"})
    
    try:
        validate_input("constellation_finder", data)
    except (ValueError, AssertionError):
        return JSONResponse(status_code=400, content={"status": "incorrect_input"})
    
    result = process_constellation_finder(data)
    return result
