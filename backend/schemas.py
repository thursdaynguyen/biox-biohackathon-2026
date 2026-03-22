from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"


class UploadResponse(BaseModel):
    session_id: str
    model_path: str


class SolutionPoint(BaseModel):
    parameters: dict[str, float]
    score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvaluateRequest(BaseModel):
    session_id: str
    parameters: dict[str, float]
    target_objective: str | None = None
    o2_bounds: list[float] | None = None


class OptimizeRequest(BaseModel):
    session_id: str
    top_k: int = Field(default=5, ge=1, le=20)
    target_objective: str | None = None


class EvaluateResponse(BaseModel):
    session_id: str
    target_objective: str | None = None
    objective_value: float
    fluxes: dict[str, float]
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class OptimumResponse(BaseModel):
    session_id: str
    target_objective: str | None = None
    optimum: SolutionPoint


class CandidatesResponse(BaseModel):
    session_id: str
    target_objective: str | None = None
    top_k: int
    candidates: list[SolutionPoint]
