from __future__ import annotations

import cobra

from backend.errors import AppError
from backend.schemas import EvaluateRequest
from backend.services.storage import model_path
from src.utils.apply_media import apply_media_and_gapfill, load_and_prep_model


def extract_fluxes(solution: cobra.Solution) -> dict[str, float]:
    fluxes = solution.fluxes
    return {
        "EX_citrate_e": float(fluxes.get("EX_citrate_e", 0.0)),
        "EX_glc__D_e": float(fluxes.get("EX_glc__D_e", 0.0)),
        "EX_nh4_e": float(fluxes.get("EX_nh4_e", 0.0)),
        "EX_o2_e": float(fluxes.get("EX_o2_e", 0.0)),
    }


def run_simulation_model(payload: EvaluateRequest) -> cobra.Solution:
    if not payload.parameters:
        raise AppError(
            code="INVALID_INPUT",
            message="At least one parameter must be provided for evaluation.",
            status_code=400,
        )

    current_model_path = model_path(payload.session_id)
    if not current_model_path.exists():
        raise AppError(
            code="MODEL_NOT_FOUND",
            message="Session model was not found.",
            status_code=404,
        )

    try:
        # model = load_and_prep_model(str(current_model_path))
        model = apply_media_and_gapfill(str(current_model_path), payload.parameters, payload.o2_bounds)
        solution = model.optimize()
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            code="CORE_EVALUATION_FAILED",
            message=f"Core evaluation failed: {exc}",
            status_code=500,
        ) from exc

    if solution.status != "optimal":
        raise AppError(
            code="CORE_EVALUATION_FAILED",
            message=f"Core evaluation returned non-optimal status: {solution.status}",
            status_code=500,
        )

    return solution
