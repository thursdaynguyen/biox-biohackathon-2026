# Architecture Notes

- **Intake**: EggNOG-mapper annotations + CarveFungi with fungal/eukaryotic universal template and biomass; outputs compartmentalized SBML.
- **Curation**: Optional gap-fill against minimal C/N/P/S + trace metals to ensure mu > 0.
- **Engine**: pFBA with oxygen unconstrained; objective defaults to biomass.
- **Pruning**: Shadow prices filter non-limiting nutrients; compute and flag C/N ratio.
- **Benchmarking**: Expose mu_max, Y_X/S, and optional titers for target metabolites.

## Service Boundaries

- **Core**: Only handles model evaluation and optimization logic.
- **Backend**: Handles upload, session/model lifecycle, request validation, error normalization, and future LLM-assisted explanation.
- **Frontend**: Only talks to the backend and never directly to core.

## Backend To Core Contract

The backend keeps a standard external API and adapts internally to whatever the current utility layer or future core implementation exposes.

Core capabilities expected by the backend:

1. Evaluate one parameter set.
2. Return one optimum point.
3. Return top-k candidate points.

Current reference in repo:

- **Evaluate one parameter set**
  Current reference:
  - `src/utils/apply_media.py::load_and_prep_model`
  - `src/utils/apply_media.py::apply_media_and_gapfill`
  - `model.optimize()` from COBRApy after media application
- **Return one optimum point**
  Current reference:
  - No stable utility function exists yet in `src/utils`
  Planned capability:
  - To be implemented by the future optimization/core layer
- **Return top-k candidate points**
  Current reference:
  - No stable utility function exists yet in `src/utils`
  Planned capability:
  - To be implemented by the future optimization/core layer

Related analysis helpers already present in the repo:

- `src/utils/evaluates.py::evaluate_shadow_prices`
- `src/utils/evaluates.py::calculate_and_tune_CN_ratio`
- `src/utils/evaluates.py::evaluate_TRY_metrics`
- `src/utils/evaluates.py::calculate_fitness_score`

Suggested internal request shapes:

```json
{
  "session_id": "abc123",
  "parameters": {
    "EX_glc__D_e": 10.0,
    "EX_nh4_e": 5.0,
    "EX_o2_e": 20.0
  },
  "target_objective": "growth"
}
```

```json
{
  "session_id": "abc123",
  "top_k": 5,
  "target_objective": "growth"
}
```

Suggested internal result shape:

```json
{
  "parameters": {
    "EX_glc__D_e": 12.0,
    "EX_nh4_e": 4.0,
    "EX_o2_e": 25.0
  },
  "score": 0.91,
  "metadata": {
    "rank": 1,
    "status": "optimal"
  }
}
```

## Frontend To Backend Contract

The frontend should only depend on these backend routes:

- `POST /api/upload`
- `POST /api/evaluate`
- `POST /api/optimum`
- `POST /api/candidates`

### Upload

`POST /api/upload`

Response:

```json
{
  "session_id": "abc123",
  "model_path": "/path/to/model.xml"
}
```

### Evaluate

`POST /api/evaluate`

Request:

```json
{
  "session_id": "abc123",
  "parameters": {
    "EX_glc__D_e": 10.0,
    "EX_nh4_e": 5.0,
    "EX_o2_e": 20.0
  },
  "target_objective": "growth"
}
```

Response:

```json
{
  "session_id": "abc123",
  "target_objective": "growth",
  "objective_value": 0.82,
  "fluxes": {
    "EX_glc__D_e": -8.4,
    "EX_nh4_e": -2.1,
    "EX_o2_e": -15.6
  },
  "diagnostics": {
    "status": "optimal"
  }
}
```

### Optimum

`POST /api/optimum`

Request:

```json
{
  "session_id": "abc123",
  "target_objective": "growth"
}
```

Response:

```json
{
  "session_id": "abc123",
  "target_objective": "growth",
  "optimum": {
    "parameters": {
      "EX_glc__D_e": 12.0,
      "EX_nh4_e": 4.0,
      "EX_o2_e": 25.0
    },
    "score": 0.91,
    "metadata": {
      "rank": 1,
      "status": "optimal"
    }
  }
}
```

### Candidates

`POST /api/candidates`

Request:

```json
{
  "session_id": "abc123",
  "top_k": 5,
  "target_objective": "growth"
}
```

Response:

```json
{
  "session_id": "abc123",
  "target_objective": "growth",
  "top_k": 5,
  "candidates": [
    {
      "parameters": {
        "EX_glc__D_e": 12.0,
        "EX_nh4_e": 4.0,
        "EX_o2_e": 25.0
      },
      "score": 0.91,
      "metadata": {
        "rank": 1,
        "status": "optimal"
      }
    }
  ]
}
```

## Error Contract

All API errors should use a normalized backend response:

```json
{
  "error": {
    "code": "MODEL_NOT_FOUND",
    "message": "Session model was not found."
  }
}
```

Recommended error codes:

- `INVALID_INPUT`
- `MODEL_NOT_FOUND`
- `MODEL_BUILD_FAILED`
- `CORE_EVALUATION_FAILED`
- `CORE_OPTIMIZATION_FAILED`

## Current Decisions

- The standard public contract is defined by the backend, not by the current utility scripts.
- The current utility layer may be adapted internally by the backend.
- `target_objective` stays as an optional reserved field until core officially supports it.
- The optimization search space is assumed to be defined by the core implementation by default.
- For the MVP demo, optimization results do not need to be persisted.

Open design items:
- Media definitions for filamentous fungi.
- Ergosterol/chitin biomass coefficients validation.
- Secondary metabolism coverage and overflow metabolism handling.
