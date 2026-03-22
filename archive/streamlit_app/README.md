MVP Media/Conditions Optimizer

This small MVP provides a Streamlit dashboard that loads SBML model files (like the CarveMe outputs in this folder), exposes extracellular species as sliders (media components), and runs a simple optimizer to search for promising media/condition settings.

Quick start

1. Create a virtualenv and install deps (optional):

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the Streamlit app:

```bash
streamlit run app.py
```

What it does

- Parses SBML/XML files in this folder or an uploaded SBML via drag & drop, and heuristically identifies extracellular species.
- Shows sliders for selected species with per-slider bounds you can tune.
- Objective options: mock growth, mock product, TRY (titer/rate/yield mock), and a scalarized multi-objective (growth + yield – byproduct penalty). Live score shown.
- Runs a random-search optimizer to suggest settings that maximize the selected objective.

Upload support

- Drag & drop SBML/XML to try a model without touching the filesystem.
- Drag & drop genome FASTA/GBK to auto-build a GEM (best-effort) via CarveMe CLI if installed.

Optional: COBRApy
Genome → GEM (experimental)

- Requires CarveMe CLI (`carve`) installed and on PATH.
- The app will write the uploaded genome to a temp file, call `carve -o <tmp>.xml <genome>`, then load the generated SBML.
- If CarveMe is not installed, the build step will fail with an explanatory error.

Flux visualization

- Enable COBRApy in the sidebar and compute FBA fluxes from current sliders.
- See top flux table and a simple flow chart (reactant→product) for the top reactions.
- (Optional) Upload an Escher map JSON to overlay fluxes on a pathway map. Requires the `escher` Python package. If not installed or map invalid, the app will fall back to the simple chart.

If you install `cobra`, the app will attempt a best-effort FBA-based evaluation (mapping sliders to exchange bounds heuristically). This is optional and may require manual mapping for best results.

Exchange mapping UI

- When COBRApy is enabled in the sidebar, a table lets you map each slider species to a specific exchange reaction ID (e.g., `EX_glc__D_e`).
- Leave blank to use heuristics; fill in to override and improve mapping reliability.

Notes on byproduct minimization and TRY

- The multi-objective adds a penalty for byproduct-like species (acetate, lactate, citrate, ethanol, etc.) and rewards yield (growth per carbon proxy).
- TRY is mock: titer = selected product slider value; rate = mock growth; yield = titer / carbon substrates proxy.

Next steps / improvements

- Add robust mapping from sliders to exchange reactions for real FBA.
- Replace the mock objective with an actual growth objective computed via FBA.
- Add advanced optimizers (Bayesian optimization) and constraints.
