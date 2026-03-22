from __future__ import annotations

import cobra

from backend.errors import AppError
from backend.schemas import EvaluateRequest
from backend.services.storage import model_path
from src.utils.apply_media import apply_media_and_gapfill, calculate_byproduct_burden
from src.utils.evaluates import evaluate_TRY_metrics


def extract_fluxes(solution: cobra.Solution, reaction_ids: list[str] | None = None) -> dict[str, float]:
    fluxes = solution.fluxes
    target_reactions = reaction_ids or []
    return {
        reaction_id: float(fluxes.get(reaction_id, 0.0))
        for reaction_id in target_reactions
    }


def normalize_medium_parameters(parameters: dict[str, float]) -> dict[str, float]:
    """Translate UI exchange-style values into cobra model.medium uptake magnitudes."""
    normalized: dict[str, float] = {}

    for reaction_id, value in parameters.items():
        numeric_value = float(value)
        normalized[reaction_id] = abs(numeric_value)

    return normalized


def run_simulation_model(payload: EvaluateRequest):
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
        model = apply_media_and_gapfill(
            str(current_model_path),
            normalize_medium_parameters(payload.parameters),
            payload.o2_bounds,
        )
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
    
    try_metrics = evaluate_TRY_metrics(model)

    byproduct_burden = calculate_byproduct_burden(str(current_model_path), solution)
    print(f" -> Total Byproduct Flux: {byproduct_burden:.4f} mmol/gDW/hr")

    return solution, byproduct_burden, try_metrics
