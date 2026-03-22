from __future__ import annotations

import cobra
from fastapi import HTTPException

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
    current_model_path = model_path(payload.session_id)
    if not current_model_path.exists():
        raise HTTPException(status_code=404, detail="Session model was not found.")

    model = load_and_prep_model(str(current_model_path))
    model = apply_media_and_gapfill(model, payload.parameters, payload.o2_bounds)
    return model.optimize()
