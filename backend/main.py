from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import HealthResponse, SimulateRequest, SimulateResponse, UploadResponse
from backend.service import create_session_from_upload, run_simulation

app = FastAPI(title="BioX Backend API", version="0.1.0")
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse()


@app.post("/api/upload", response_model=UploadResponse)
async def upload_genome(file: UploadFile = File(...)) -> UploadResponse:
    return await create_session_from_upload(file)


@app.post("/api/simulate", response_model=SimulateResponse)
async def simulate(payload: SimulateRequest) -> SimulateResponse:
    return run_simulation(payload)
