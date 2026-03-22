# MediaOpt (Hackathon MVP)

MediaOpt builds and evaluates genome-scale metabolic models (GEMs) for filamentous fungi. The demo flow takes a protein FASTA upload, auto-builds an SBML model with CarveMe, applies custom media bounds, runs COBRApy optimization, and returns flux diagnostics plus simple candidate suggestions.

## What this MVP does
- Accepts protein FASTA uploads and builds a GEM via the CarveMe CLI.
- Runs pFBA-style simulations with user-provided media parameters and reports key exchange fluxes.
- Surfaces placeholder optimum/top-k candidates (hooks ready for a future optimizer core).
- Ships a Vite/Vue UI for uploads, slider-based media tweaks, and viewing mock optimization profiles.
- Provides a SMAC3-based script for offline media search experimentation (optional).

## Tech stack
- Backend: FastAPI, Pydantic, Uvicorn, COBRApy, CarveMe runner, python-multipart.
- Frontend: Vite 6, Vue 3 single-page app.
- Optimization sandbox: SMAC3 + ConfigSpace (naive Bayesian search over media bounds).
- Utilities: pandas, numpy, Biopython. OpenAI client is present but LLM features are disabled by default.

## Quickstart
Backend
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Frontend
```bash
cd frontend
npm install
npm run dev
```

## API surface (current)
- POST /api/upload — upload protein FASTA; returns session_id and SBML path.
- POST /api/evaluate — run a simulation with media bounds and return objective + fluxes.
- POST /api/optimum — placeholder optimum point (to be wired to real optimizer).
- POST /api/candidates — placeholder top-k candidate set.

## Repo map (active parts)
- backend/: FastAPI app, schemas, orchestration, storage (CarveMe), simulation helpers.
- src/utils/: model utilities (apply media, byproduct burden), CarveMe CLI wrapper, SMAC3 tuner.
- frontend/: Vite + Vue SPA for upload and exploration UI.
- data/sessions/: sample session artifacts (FASTA, SBML, TSV) for demo/testing.
- docs/ARCHITECTURE.md: high-level design notes and contracts.

## Notable workflows
- Model build: protein FASTA → CarveMe CLI → SBML saved under data/sessions/<session_id>/model.xml.
- Simulation: media bounds applied via COBRApy → model.optimize() → flux extraction + diagnostics.
- Offline tuning (optional): run `python src/utils/tune_media.py --gem-fpath <path/to/model.xml>` for SMAC3 search over media bounds.

## Status and gaps
- LLM/explanation features are stubbed; `is_llm_enabled` returns false.
- Optimizer endpoints return placeholder data; integrating a real search core is future work.
- No Dockerfile is provided; use venv + requirements.txt for now.

## Contributing / dev tips
- Lint/tests: `ruff check backend src` and add pytest once tests are introduced.
- Keep CarveMe installed and `carve` on PATH for upload flows.
- Session outputs live in data/sessions/<session_id>/; clean as needed between runs.
