from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import cobra
from fastapi import HTTPException, UploadFile

from backend.schemas import RecommendationItem, SimulateRequest, SimulateResponse, UploadResponse
from src.utils.apply_media import apply_media_and_gapfill, load_and_prep_model

BASE_DIR = Path(__file__).resolve().parents[1]
SESSIONS_DIR = BASE_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_dir(session_id: str) -> Path:
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _model_path(session_id: str) -> Path:
    return _session_dir(session_id) / "model.xml"


def _extract_fluxes(solution: cobra.Solution) -> dict[str, float]:
    fluxes = solution.fluxes
    return {
        "EX_citrate_e": float(fluxes.get("EX_citrate_e", 0.0)),
        "EX_glc__D_e": float(fluxes.get("EX_glc__D_e", 0.0)),
        "EX_nh4_e": float(fluxes.get("EX_nh4_e", 0.0)),
        "EX_o2_e": float(fluxes.get("EX_o2_e", 0.0)),
    }


def _build_placeholder_recommendations(media: dict[str, float]) -> list[RecommendationItem]:
    recommendations: list[RecommendationItem] = []

    if media.get("EX_glc__D_e", 0.0) <= 5:
        recommendations.append(
            RecommendationItem(
                id="EX_glc__D_e",
                label="Glucose",
                direction="increase",
                reason="Carbon input is low relative to common growth settings.",
                confidence=0.55,
            )
        )

    if media.get("EX_nh4_e", 0.0) <= 2:
        recommendations.append(
            RecommendationItem(
                id="EX_nh4_e",
                label="Ammonium",
                direction="increase",
                reason="Nitrogen availability may constrain biomass formation.",
                confidence=0.5,
            )
        )

    if not recommendations:
        recommendations.append(
            RecommendationItem(
                id="baseline",
                label="Current media",
                direction="keep",
                reason="No simple heuristic adjustment was triggered.",
                confidence=0.3,
            )
        )

    return recommendations


def _run_carveme(input_path: Path, output_path: Path) -> None:
    script_path = BASE_DIR / "src" / "utils" / "run_carveme.py"
    if not script_path.exists():
        raise HTTPException(status_code=500, detail="CarveMe runner script is missing.")

    process = subprocess.run(
        [
            sys.executable,
            str(script_path),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )

    if process.returncode != 0:
        error_message = (process.stderr or process.stdout or "").strip()
        raise HTTPException(
            status_code=500,
            detail=f"CarveMe failed to build a GEM. {error_message}",
        )


def _validate_model(model_path: Path) -> None:
    try:
        cobra.io.read_sbml_model(model_path)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded sequence did not produce a valid SBML model: {exc}",
        ) from exc


async def create_session_from_upload(file: UploadFile) -> UploadResponse:
    session_id = os.urandom(6).hex()
    session_dir = _session_dir(session_id)
    input_path = session_dir / file.filename
    model_path = _model_path(session_id)

    with input_path.open("wb") as output_file:
        output_file.write(await file.read())

    _run_carveme(input_path=input_path, output_path=model_path)
    _validate_model(model_path)

    return UploadResponse(session_id=session_id, model_path=str(model_path))


def run_simulation(payload: SimulateRequest) -> SimulateResponse:
    model_path = _model_path(payload.session_id)
    if not model_path.exists():
        raise HTTPException(status_code=404, detail="Session model was not found.")

    model = load_and_prep_model(str(model_path))
    model = apply_media_and_gapfill(model, payload.media, payload.o2_bounds)
    solution = model.optimize()

    return SimulateResponse(
        session_id=payload.session_id,
        objective_value=float(solution.objective_value),
        fluxes=_extract_fluxes(solution),
        recommendations=_build_placeholder_recommendations(payload.media),
        diagnostics={
            "status": solution.status,
            "target_objective": payload.target_objective or "growth",
        },
    )
