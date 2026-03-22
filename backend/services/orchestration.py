from __future__ import annotations

from fastapi import UploadFile

from backend.errors import AppError
from backend.schemas import (
    CandidatesResponse,
    EvaluateRequest,
    EvaluateResponse,
    OptimizeRequest,
    OptimumResponse,
    UploadResponse,
)
from backend.services.optimization import build_optimum_point, build_topk_candidates
from backend.services.simulation import extract_fluxes, run_simulation_model
from backend.services.storage import create_session_from_upload, model_path


async def create_upload_session(file: UploadFile) -> UploadResponse:
    return await create_session_from_upload(file)


def evaluate_parameters(payload: EvaluateRequest) -> EvaluateResponse:
    solution = run_simulation_model(payload)
    return EvaluateResponse(
        session_id=payload.session_id,
        target_objective=payload.target_objective,
        objective_value=float(solution.objective_value),
        fluxes=extract_fluxes(solution),
        diagnostics={
            "status": solution.status,
            "parameter_count": len(payload.parameters),
            "objective_mode": payload.target_objective or "default",
        },
    )


def get_optimum(payload: OptimizeRequest) -> OptimumResponse:
    if not model_path(payload.session_id).exists():
        raise AppError(
            code="MODEL_NOT_FOUND",
            message="Session model was not found.",
            status_code=404,
        )

    optimum = build_optimum_point(
        parameters={},
        score=None,
    )
    return OptimumResponse(
        session_id=payload.session_id,
        target_objective=payload.target_objective,
        optimum=optimum,
    )


def get_topk_candidates(payload: OptimizeRequest) -> CandidatesResponse:
    if not model_path(payload.session_id).exists():
        raise AppError(
            code="MODEL_NOT_FOUND",
            message="Session model was not found.",
            status_code=404,
        )

    candidates = build_topk_candidates(
        parameters={},
        base_score=None,
        top_k=payload.top_k,
    )
    return CandidatesResponse(
        session_id=payload.session_id,
        target_objective=payload.target_objective,
        top_k=payload.top_k,
        candidates=candidates,
    )
