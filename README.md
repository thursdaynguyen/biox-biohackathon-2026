# MediaOpt MVP (Filamentous Fungi)

Pragmatic, modular stack to take a fungal genome, auto-generate a compartmentalized GEM with EggNOG-mapper + CarveFungi, curate it for growth, run pFBA with oxygen unconstrained, and surface a minimal media lever set using shadow prices and C/N ratios.

## Why this repo
- Filamentous fungi need a eukaryotic template (chitin/ergosterol biomass) and compartment-aware SBML.
- Overflow metabolism is common; pFBA plus C/N flagging keeps the focus on biomass vs. byproducts.
- Shadow prices collapse dimensionality so non-specialists can tweak the levers that matter.

## Stack
- Python 3.10+ with `carveme`, `cobra`, `pandas`, `numpy`.
- FastAPI for a thin upload + simulation API; CLI wrapper for offline runs.
- Optional: Docker for reproducible runs.

## Workflow (high level)
1) Intake: upload `.fasta`/`.gbk` → EggNOG-mapper annotations + CarveFungi using the eukaryotic/fungal template → SBML with compartments and fungal biomass.
2) Decision: "Fast Draft" vs. "High Fidelity"; optional gap-fill against minimal C/N/P/S + trace metals.
3) Engine: pFBA with oxygen unconstrained (lower bound -1000 mmol/gDW/h by default).
4) Pruning: shadow prices + computed C/N ratio; flag carbon and nitrogen sources as primary levers.
5) Benchmarking: surface theoretical `mu_max`, `Y_X/S`, and optional product titers.

## Repo layout
- src/mediaopt: pipeline modules (`intake`, `curation`, `simulation`, `pruning`, `benchmarking`), FastAPI entrypoint, schemas, config.
- data/templates: placeholder for fungal universal template, media recipes, biomass coefficients.
- docs: design notes and decisions.
- tests: lightweight smoke and unit scaffolding.
- notebooks: space for exploratory analyses.

## Backend (FastAPI)
```bash
# from repo root, create/activate env
python -m venv .venv
source .venv/bin/activate

# install deps
pip install -r requirements.txt

# start API (dev)
uvicorn src.server.main:app --reload
```

Notes:
- Endpoints are rooted at `/api` (upload, simulate, trajectory, finalize).
- Websocket stream lives at `/api/stream` and broadcasts metrics.
- CarveMe must be available in the environment for uploads to succeed.

## Frontend (Vite/React)
```bash
cd frontend
npm install
npm run dev
```

Notes:
- The frontend expects the backend on the same host/port; when running separately, set up a dev proxy or serve the built frontend from the backend host.
- Upload accepts `.faa` files; simulation controls adjust media sliders and consume `/api/simulate`.

## Development
- Lint/tests (backend): `ruff check src tests` and `pytest -q`
- Data/session outputs land in `data/sessions/<session_id>/`.