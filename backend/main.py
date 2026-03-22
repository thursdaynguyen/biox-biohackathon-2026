from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import (
    CandidatesResponse,
    EvaluateRequest,
    EvaluateResponse,
    HealthResponse,
    OptimizeRequest,
    OptimumResponse,
    UploadResponse,
)
from backend.services.orchestration import (
    create_upload_session,
    evaluate_parameters,
    get_optimum,
    get_topk_candidates,
)

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
    return await create_upload_session(file)


@app.post("/api/evaluate", response_model=EvaluateResponse)
async def evaluate(payload: EvaluateRequest) -> EvaluateResponse:
    return evaluate_parameters(payload)


@app.post("/api/optimum", response_model=OptimumResponse)
async def optimum(payload: OptimizeRequest) -> OptimumResponse:
    return get_optimum(payload)


@app.post("/api/candidates", response_model=CandidatesResponse)
async def candidates(payload: OptimizeRequest) -> CandidatesResponse:
    return get_topk_candidates(payload)
