from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import cobra
from fastapi import HTTPException, UploadFile

from backend.schemas import UploadResponse

BASE_DIR = Path(__file__).resolve().parents[2]
SESSIONS_DIR = BASE_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def session_dir(session_id: str) -> Path:
    target_dir = SESSIONS_DIR / session_id
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def model_path(session_id: str) -> Path:
    return session_dir(session_id) / "model.xml"


def run_carveme(input_path: Path, output_path: Path) -> None:
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


def validate_model(path: Path) -> None:
    try:
        cobra.io.read_sbml_model(path)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded sequence did not produce a valid SBML model: {exc}",
        ) from exc


async def create_session_from_upload(file: UploadFile) -> UploadResponse:
    session_id = os.urandom(6).hex()
    current_session_dir = session_dir(session_id)
    input_path = current_session_dir / file.filename
    output_path = model_path(session_id)

    with input_path.open("wb") as output_file:
        output_file.write(await file.read())

    run_carveme(input_path=input_path, output_path=output_path)
    validate_model(output_path)

    return UploadResponse(session_id=session_id, model_path=str(output_path))

