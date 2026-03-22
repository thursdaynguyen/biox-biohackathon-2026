from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import cobra
from fastapi import UploadFile

from backend.errors import AppError
from backend.schemas import UploadResponse

BASE_DIR = Path(__file__).resolve().parents[2]
SESSIONS_DIR = BASE_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_UPLOAD_SUFFIXES = {".faa", ".fa", ".fasta"}


def session_dir(session_id: str) -> Path:
    target_dir = SESSIONS_DIR / session_id
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def model_path(session_id: str) -> Path:
    return session_dir(session_id) / "model.xml"


def run_carveme(input_path: Path, output_path: Path) -> None:
    script_path = BASE_DIR / "src" / "utils" / "run_carveme.py"
    if not script_path.exists():
        raise AppError(
            code="MODEL_BUILD_FAILED",
            message="CarveMe runner script is missing.",
            status_code=500,
        )

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
        if "CarveMe CLI was not found" in error_message or "No such file or directory: 'carve'" in error_message:
            raise AppError(
                code="MODEL_BUILD_FAILED",
                message="CarveMe CLI is not installed or `carve` is not available on PATH.",
                status_code=500,
            )
        raise AppError(
            code="MODEL_BUILD_FAILED",
            message=f"CarveMe failed to build a GEM. {error_message}",
            status_code=500,
        )

    if not output_path.exists():
        error_message = (process.stderr or process.stdout or "").strip()
        raise AppError(
            code="MODEL_BUILD_FAILED",
            message=(
                "CarveMe finished without producing an SBML model file. "
                f"Expected output: {output_path}. "
                f"Details: {error_message or 'No output was reported.'}"
            ),
            status_code=500,
        )


def validate_model(path: Path) -> None:
    try:
        cobra.io.read_sbml_model(path)
    except Exception as exc:
        raise AppError(
            code="INVALID_INPUT",
            message=f"Uploaded sequence did not produce a valid SBML model: {exc}",
            status_code=400,
        ) from exc


async def create_session_from_upload(file: UploadFile) -> UploadResponse:
    if not file.filename:
        raise AppError(
            code="INVALID_INPUT",
            message="Uploaded file must include a filename.",
            status_code=400,
        )

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise AppError(
            code="INVALID_INPUT",
            message="Unsupported file type. Please upload a protein FASTA file (.faa, .fa, or .fasta).",
            status_code=400,
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise AppError(
            code="INVALID_INPUT",
            message="Uploaded file is empty.",
            status_code=400,
        )

    session_id = os.urandom(6).hex()
    current_session_dir = session_dir(session_id)
    input_path = current_session_dir / file.filename
    output_path = model_path(session_id)

    with input_path.open("wb") as output_file:
        output_file.write(file_bytes)

    run_carveme(input_path=input_path, output_path=output_path)
    validate_model(output_path)

    return UploadResponse(session_id=session_id, model_path=str(output_path))
