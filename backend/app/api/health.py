"""
Health check endpoint for Open Karaoke Studio FastAPI backend.
"""

import asyncio
import time
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    framework: str
    timestamp: datetime
    response_time_ms: float


@router.get("/health", response_model=HealthResponse)
async def health():
    """
    Health check endpoint with performance timing.
    Compare this with Flask's health endpoint to see performance improvements.
    """
    start_time = time.time()

    # Simulate some async work
    await asyncio.sleep(0.001)

    end_time = time.time()
    response_time = (end_time - start_time) * 1000  # Convert to milliseconds

    return HealthResponse(
        status="ok",
        framework="fastapi",
        timestamp=datetime.now(),
        response_time_ms=round(response_time, 2),
    )
