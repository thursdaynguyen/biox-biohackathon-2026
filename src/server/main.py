from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

import cobra
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.utils.apply_media import apply_media_and_gapfill, load_and_prep_model
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
SESSIONS_DIR = BASE_DIR / "data" / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = BASE_DIR / "tmp"
TMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="BioX GEM Dashboard API", version="0.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"]
)


class SimulateRequest(BaseModel):
    session_id: str
    media: Dict[str, float]
    o2_bounds: Optional[List[float]] = None


class TrajectoryAppend(BaseModel):
    session_id: str
    media: Dict[str, float]
    metrics: Dict


class FinalizeRequest(BaseModel):
    session_id: str
    final_metrics: Dict


class StreamBroker:
    def __init__(self) -> None:
        self.connections: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self.lock:
            self.connections.append(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self.lock:
            if ws in self.connections:
                self.connections.remove(ws)

    async def broadcast(self, message: Dict) -> None:
        async with self.lock:
            conns = list(self.connections)
        for ws in conns:
            try:
                await ws.send_json(message)
            except WebSocketDisconnect:
                await self.disconnect(ws)
            except Exception:
                await self.disconnect(ws)


stream = StreamBroker()


def _session_dir(session_id: str) -> Path:
    d = SESSIONS_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _model_path(session_id: str) -> Path:
    return _session_dir(session_id) / "model.xml"


def _save_upload(tmp_path: Path, dest: Path) -> None:
    if not tmp_path.exists():
        raise FileNotFoundError(
            f"Expected temporary model at {tmp_path} but it does not exist"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tmp_path, dest)


def _run_carveme(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Integrate with existing run_carveme.py script if available
    script = BASE_DIR / "src" / "utils" / "run_carveme.py"
    if not script.exists():
        # Let the exception surface to show stack trace in server logs
        raise FileNotFoundError("CarveMe runner not found at src/utils/run_carveme.py")

    proc = subprocess.run(
        [
            "python",
            str(script),
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        stdout = (proc.stdout or "").strip()
        # Surface full stdout/stderr by raising a runtime error (shows in server logs)
        raise RuntimeError(
            f"CarveMe failed (exit {proc.returncode}). stderr: {stderr or stdout}"
        )
    if not output_path.exists():
        raise RuntimeError(
            f"CarveMe did not produce an SBML file at {output_path}. stderr/stdout: {(proc.stderr or proc.stdout or '').strip()}"
        )


def _validate_sbml(path: Path) -> None:
    """Ensure file is readable SBML; raise HTTPException if invalid."""
    try:
        cobra.io.read_sbml_model(path)
    except Exception as exc:  # cobra raises CobraSBMLError
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded genome did not produce a valid SBML model: {exc}",
        ) from exc


def _load_model(session_id: str) -> cobra.Model:
    model_file = _model_path(session_id)
    if not model_file.exists():
        raise FileNotFoundError(f"Model for session {session_id} not found")
    return load_and_prep_model(str(model_file))


def _extract_metrics(solution: cobra.Solution) -> Dict:
    fluxes = solution.fluxes
    payload = {
        "objective_value": float(solution.objective_value),
        "fluxes": {
            "EX_citrate_e": float(fluxes.get("EX_citrate_e", 0.0)),
            "EX_glc__D_e": float(fluxes.get("EX_glc__D_e", 0.0)),
        },
    }
    return payload


@app.post("/api/upload")
async def upload_genome(file: UploadFile = File(...)):
    session_id = os.urandom(6).hex()
    work_dir = _session_dir(session_id)
    tmp = work_dir / file.filename
    with tmp.open("wb") as f:
        f.write(await file.read())

    model_path = _model_path(session_id)
    temp_out = model_path  # write SBML directly into the session folder
    _run_carveme(tmp, temp_out)
    _validate_sbml(temp_out)

    return {"session_id": session_id, "model_path": str(model_path)}


@app.post("/api/simulate")
async def simulate(body: SimulateRequest):
    model = _load_model(body.session_id)
    model = apply_media_and_gapfill(model, body.media, body.o2_bounds)
    sol = model.optimize()
    metrics = _extract_metrics(sol)

    record = {"timestamp": asyncio.get_event_loop().time(), **metrics}
    await stream.broadcast({"type": "metrics", "payload": record})
    return record


@app.post("/api/trajectory")
async def append_trajectory(body: TrajectoryAppend):
    traj_path = _session_dir(body.session_id) / "trajectory.jsonl"
    with traj_path.open("a") as f:
        f.write(json.dumps({"media": body.media, "metrics": body.metrics}) + "\n")
    return {"ok": True}


@app.post("/api/finalize")
async def finalize(body: FinalizeRequest):
    report_path = _session_dir(body.session_id) / "final.json"
    with report_path.open("w") as f:
        json.dump(body.final_metrics, f)
    return {"ok": True}


@app.websocket("/api/stream")
async def stream_ws(ws: WebSocket):
    await stream.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        await stream.disconnect(ws)
    except Exception:
        await stream.disconnect(ws)
