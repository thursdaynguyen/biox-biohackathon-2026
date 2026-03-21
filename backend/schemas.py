from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class UploadResponse(BaseModel):
    session_id: str
    model_path: str


class RecommendationItem(BaseModel):
    id: str
    label: str
    direction: str
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SimulateRequest(BaseModel):
    session_id: str
    media: dict[str, float]
    target_objective: str | None = None
    o2_bounds: list[float] | None = None


class SimulateResponse(BaseModel):
    session_id: str
    objective_value: float
    fluxes: dict[str, float]
    recommendations: list[RecommendationItem]
    diagnostics: dict[str, Any] = Field(default_factory=dict)
