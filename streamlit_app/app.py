import os
import io
import uuid
import json
from pathlib import Path
import streamlit as st
import altair as alt
from typing import Dict, Tuple, List
from parser import parse_sbml_extracellular
from optimizer import objective_mock, objective_mock_multi, random_search, try_cobra_fba, run_cobra_flux_distribution
from utils import compute_try, compute_growth_score
from flux_viz import flux_table, flux_edges, escher_html, plotly_sankey
from run_carveme import run_carveme
from apply_media import load_and_prep_model, apply_media_and_gapfill, calculate_byproduct_burden
from evaluates import evaluate_TRY_metrics

# Fixed set of exchange reactions exposed as sliders; labels are user-friendly while ids feed the backend.
KEY_EXCHANGE_SPECIES = [
    {'id': 'EX_glc__D_e', 'label': 'D-Glucose', 'aliases': ['glc__D_e']},
    {'id': 'EX_pi_e', 'label': 'Phosphate', 'aliases': ['pi_e']},
    {'id': 'EX_o2_e', 'label': 'Oxygen', 'aliases': ['o2_e']},
    {'id': 'EX_glyc_e', 'label': 'Glycerol', 'aliases': ['glyc_e']},
    {'id': 'EX_nh4_e', 'label': 'Ammonium', 'aliases': ['nh4_e']},
    {'id': 'EX_so4_e', 'label': 'Sulfate', 'aliases': ['so4_e']},
    {'id': 'EX_xyl__D_e', 'label': 'D-Xylose', 'aliases': ['xyl__D_e']},
    {'id': 'EX_cellb_e', 'label': 'Cellobiose', 'aliases': ['cellb_e']},
]

DEFAULT_MEDIA = {
    'EX_glc__D_e': 10.0,
    'EX_nh4_e': 10.0,
    'EX_pi_e': 10.0,
    'EX_so4_e': 3.0,
    'EX_h2o_e': 10.0,
    'EX_h_e': 10.0,
    'EX_o2_e': 10.0,
}

MODELS_DIR = Path(__file__).resolve().parent
OUTPUT_SESSIONS_DIR = MODELS_DIR.parent / 'outputs' / 'sessions'
BIONX_TUNING_RESULTS = MODELS_DIR.parent / 'resources' / 'biox_tuning_results.json'

st.set_page_config(page_title="MVP Media Optimizer", layout='wide')
st.title('MediaOpt from BioX')

def _ensure_session_dir() -> Path:
    if 'carveme_session_id' not in st.session_state:
        st.session_state['carveme_session_id'] = uuid.uuid4().hex[:12]
    session_dir = OUTPUT_SESSIONS_DIR / st.session_state['carveme_session_id']
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _load_reference_config(path: Path) -> Dict | None:
    try:
        with path.open('r', encoding='utf-8') as fh:
            data = json.load(fh)
        for _, entries in data.items():
            if isinstance(entries, list) and entries:
                cfg = entries[0].get('config') if isinstance(entries[0], dict) else None
                if isinstance(cfg, dict):
                    return cfg
    except Exception:
        return None
    return None


def _discover_models(extra_paths: List[Path] | None = None) -> List[Tuple[str, Path]]:
    models: List[Tuple[str, Path]] = []
    for p in MODELS_DIR.iterdir():
        if p.suffix.lower() in ['.xml', '.sbml']:
            models.append((p.name, p))
    if OUTPUT_SESSIONS_DIR.exists():
        for p in OUTPUT_SESSIONS_DIR.glob('**/*.xml'):
            label = f"session/{p.parent.name}/{p.name}"
            models.append((label, p))
    if extra_paths:
        for p in extra_paths:
            if p is None:
                continue
            label = p.name
            if OUTPUT_SESSIONS_DIR in p.parents:
                label = f"session/{p.parent.name}/{p.name}"
            if not any(existing[1] == p for existing in models):
                models.append((label, p))
    return models


# Sidebar: model selection or upload
st.sidebar.header('Model selection')
st.sidebar.subheader('Upload genome (FASTA/GBK) to auto-build GEM')
genome_upload = st.sidebar.file_uploader('Drag & drop genome file', type=['fasta', 'fa', 'fna', 'faa', 'gbk', 'gb'])

st.sidebar.subheader('Or upload SBML directly')
uploaded = st.sidebar.file_uploader('SBML/XML file', type=['xml', 'sbml'])

use_uploaded = uploaded is not None
use_genome = genome_upload is not None
model_path: Path | None = None
generated_model: Path | None = None

if use_genome:
    st.sidebar.info('Genome upload detected; will attempt to build GEM via CarveMe if available.')
    session_dir = _ensure_session_dir()
    upload_path = session_dir / genome_upload.name
    with open(upload_path, 'wb') as fh:
        fh.write(genome_upload.getvalue())
    output_path = session_dir / 'model.xml'

    # Avoid re-running if already built in this session with same name
    rerun_needed = True
    if st.session_state.get('carveme_model_path') == str(output_path) and output_path.exists():
        rerun_needed = False

    if rerun_needed:
        with st.spinner('Running CarveMe to build GEM...'):
            try:
                run_carveme(fasta_path=upload_path, output_path=output_path)
                st.session_state['carveme_model_path'] = str(output_path)
                st.sidebar.success('GEM built via CarveMe and stored in outputs/sessions.')
            except Exception as e:
                st.sidebar.error(f'CarveMe run failed: {e}')
                st.stop()
    generated_model = output_path
    model_path = output_path
elif use_uploaded:
    st.sidebar.success('Using uploaded SBML/XML (session-only)')
    import tempfile
    fd, tmp_path = tempfile.mkstemp(suffix='.xml')
    with os.fdopen(fd, 'wb') as f:
        f.write(uploaded.read())
    model_path = Path(tmp_path)

# Always offer selection, including generated/uploaded model
discovered = _discover_models(extra_paths=[generated_model, model_path if use_uploaded else None])
if not discovered:
    st.sidebar.warning('No SBML/XML model files found in the project folder or outputs.')
    st.stop()

labels = [label for label, _ in discovered]
default_index = 0
preferred_path = None
if generated_model:
    preferred_path = generated_model
elif use_uploaded:
    preferred_path = model_path
elif 'carveme_model_path' in st.session_state:
    preferred_path = Path(st.session_state['carveme_model_path'])

if preferred_path:
    for idx, (_, p) in enumerate(discovered):
        if str(p) == str(preferred_path):
            default_index = idx
            break

selected_label = st.sidebar.selectbox('Choose a model file', labels, index=default_index)
model_path = dict(discovered)[selected_label]

# Optimizer settings removed from sidebar; using defaults
objective_choice = 'Growth Rate'
n_iter = 500
attempt_cobra = False

# Build / load the selected model
with st.spinner('Loading model...'):
    if model_path is None:
        st.error('No model path resolved.')
        st.stop()
    species_e = parse_sbml_extracellular(str(model_path))
    model_path_for_cobra = str(model_path)

st.markdown(f'**Found {len(species_e)} extracellular species** (heuristic).')

# Restrict selection to the fixed set of exchange reactions with friendly display names
species_lookup = {s['id']: s for s in species_e}

def _norm_id(raw: str) -> str:
    if not raw:
        return ''
    r = raw.lower()
    # strip brackets like [e]
    if r.startswith('[') and ']' in r:
        r = r[r.index(']')+1:]
    r = r.replace('[e]', '').replace('(e)', '')
    # strip leading ex_
    if r.startswith('ex_'):
        r = r[3:]
    # common compartment suffixes
    for suf in ['_e0', '_e1', '_e', '-e', '.e', '_ext', '_b']:
        if r.endswith(suf):
            r = r[:-len(suf)]
            break
    return r

# Build a normalized lookup to catch naming differences
normalized_lookup = {}
for sid, sdata in species_lookup.items():
    key = sid.lower()
    normalized_lookup.setdefault(key, sdata)
    # normalized_lookup.setdefault(_norm_id(sid), sdata)

# also add aliases directly from KEY_EXCHANGE_SPECIES to avoid warnings when present in model

configured_species = []
missing_species = []
resolved_aliases = {}
for spec in KEY_EXCHANGE_SPECIES:
    desired_id = spec['id']
    label = spec['label']
    aliases = spec.get('aliases', [])
    candidates = [desired_id] + aliases
    base = None
    matched_id = None

    # exact or normalized candidate match
    for cid in candidates:
        if cid in species_lookup:
            matched_id = cid
            base = species_lookup[cid]
            break
        norm = cid.lower()
        if norm in normalized_lookup:
            matched_id = normalized_lookup[norm]['id']
            base = normalized_lookup[norm]
            break

    # heuristic: case-insensitive contains match on normalized ids
    if base is None:
        target = desired_id.lower()
        for norm_id, sdata in normalized_lookup.items():
            if target in norm_id:
                matched_id = sdata['id']
                base = sdata
                break

    if base is None:
        missing_species.append(desired_id)
        base = {'id': desired_id, 'name': label, 'compartment': '', 'boundaryCondition': False, 'formula': None}
    else:
        resolved_aliases[desired_id] = matched_id if matched_id != desired_id else None

    configured_species.append({**base, 'display_name': label})

if missing_species:
    st.warning(f"Some configured exchange species were not found in the model and will use placeholders (FBA mapping may skip them): {', '.join(missing_species)}")
if resolved_aliases:
    resolved_details = [f"{k} → {v}" for k, v in resolved_aliases.items() if v]
    if resolved_details:
        st.info(f"Matched configured species to model ids: {', '.join(resolved_details)}")

species_options = [s['id'] for s in configured_species]
species_display = {s['id']: s.get('display_name', s.get('name', s['id'])) for s in configured_species}
selected_species = st.multiselect(
    'Choose species to expose as sliders (select key nutrients/products)',
    species_options,
    default=species_options,
    format_func=lambda sid: species_display.get(sid, sid)
)
species_map = {s['id']: s for s in configured_species}

bounds: Dict[str, Tuple[float, float]] = {}
default_vals: Dict[str, float] = {}
with st.expander('Slider bounds / fine-tuning', expanded=False):
    if selected_species:
        for key in selected_species:
            s = species_map[key]
            sid = s['id']
            friendly_label = f"{species_display.get(sid, sid)} ({sid})"
            cols = st.columns([1, 1, 1])
            min_v = cols[0].number_input(f'{friendly_label} min', value=-15.0, step=0.1, key=f'{sid}_min')
            max_v = cols[1].number_input(f'{friendly_label} max', value=15.0, step=0.1, key=f'{sid}_max')
            default_v = cols[2].number_input(
                f'{friendly_label} default',
                value=DEFAULT_MEDIA.get(sid, 0.0),
                step=0.1,
                key=f'{sid}_def'
            )
            # sanitize
            if max_v < min_v:
                max_v = min_v
            bounds[sid] = (float(min_v), float(max_v))
            default_vals[sid] = float(default_v)
    else:
        st.info('Pick some species to customize slider bounds.')

st.markdown('### Media')
slider_values: Dict[str, float] = {}
if selected_species:
    cols = st.columns(2)
    for i, key in enumerate(selected_species):
        s = species_map[key]
        col = cols[i % len(cols)]
        sid = s['id']
        lo, hi = bounds.get(sid, (-15.0, 15.0))
        friendly_label = species_display.get(sid, s.get('name', sid))
        val = col.slider(
            friendly_label,
            min_value=lo,
            max_value=hi,
            value=default_vals.get(sid, DEFAULT_MEDIA.get(sid, (lo + hi) / 2)),
            step=max((hi - lo) / 100.0, 0.01),
            key=sid
        )
        slider_values[sid] = float(val)

# Optional exchange mapping for COBRApy
exchange_map: Dict[str, str] = {}
if selected_species and attempt_cobra:
    st.markdown('### Exchange reaction mapping (for FBA)')
    st.caption('Map slider species to exchange reaction IDs in the SBML (e.g., EX_glc__D_e). Leave blank to use heuristics.')
    for key in selected_species:
        s = species_map[key]
        sid = s['id']
        default_guess = f"EX_{sid}" if not sid.upper().startswith('EX_') else sid
        friendly_label = species_display.get(sid, sid)
        rid = st.text_input(f'Reaction for {friendly_label} ({sid})', value='', placeholder=default_guess, key=f'map_{sid}')
        if rid.strip():
            exchange_map[sid] = rid.strip()

# Live objective preview
if selected_species:
    if objective_choice == 'Growth Rate':
        # Compute growth and related metrics (TRY + byproduct burden) in one pass
        try:
            model = load_and_prep_model(model_path_for_cobra)
            model.medium = model.medium.copy()
            apply_media_and_gapfill(model, media=slider_values, merge_with_existing=True)
            solution = model.optimize()
            growth_score = float(solution.objective_value) if solution.status == 'optimal' else 0.0
            try_metrics = evaluate_TRY_metrics(model)
            burden = calculate_byproduct_burden(model_path_for_cobra, solution)

            cols = st.columns(5)
            cols[0].metric('Growth Rate', f"{growth_score:.3f}")
            cols[1].metric('Titer', f"{try_metrics.get('Titer', 0.0):.4f}")
            cols[2].metric('Rate', f"{try_metrics.get('Rate', 0.0):.4f}")
            cols[3].metric('Yield', f"{try_metrics.get('Yield', 0.0):.4f}")
            cols[4].metric('Byproduct burden', f"{burden:.4f}")
        except Exception as e:
            st.error(f'Failed to compute metrics: {e}')
    elif objective_choice == 'Mock product':
        st.info('Pick the product species below and the mock objective will use product concentration as titer proxy.')
    elif objective_choice == 'Growth+Yield - Byproducts':
        score = objective_mock_multi([species_map[f] for f in selected_species], slider_values,
                                     weight_yield=weight_yield, weight_growth=weight_growth,
                                     weight_byproduct=weight_byprod)
        st.metric('Growth+Yield-Byproducts score', f"{score:.3f}")
    else:
        st.info('TRY will be computed from selected product and substrates (mock calculations).')

st.markdown('### Optimization')
run_opt = st.button('Run optimizer')
# product_choice = None
# if objective_choice in ['Mock product', 'TRY (titer/rate/yield)']:
#     product_options = ['-- none --'] + selected_species
#     product_choice = st.selectbox(
#         'Select product species (for titer/rate/yield calculations)',
#         product_options,
#         format_func=lambda sid: species_display.get(sid, sid) if sid != '-- none --' else '-- none --'
#     )
if run_opt:
    # Display reference config from resources/biox_tuning_results.json
    try:
        with open(BIONX_TUNING_RESULTS, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        first_key = next(iter(data)) if isinstance(data, dict) and data else None
        entries = data.get(first_key, []) if first_key else []
        cfg = entries[0].get('config') if entries and isinstance(entries[0], dict) else None
        if cfg:
            # Single-row table of the eight exchange bounds
            label_lookup = {spec['id']: spec['label'] for spec in KEY_EXCHANGE_SPECIES}
            pretty_row = {}
            for spec in KEY_EXCHANGE_SPECIES:
                sid = spec['id']
                label = label_lookup.get(sid, sid)
                # Align value by id first, then any alias if present
                val = cfg.get(sid, None)
                if val is None:
                    for alias in spec.get('aliases', []):
                        if alias in cfg:
                            val = cfg[alias]
                            break
                pretty_row[label] = val
            # Include any unexpected keys at the end
            for k, v in cfg.items():
                if k not in label_lookup and k not in pretty_row:
                    pretty_row[k] = v
            st.table([pretty_row])
        else:
            st.info('No config found in biox_tuning_results.json.')
    except Exception as e:
        st.error(f'Failed to load biox_tuning_results.json: {e}')

# Flux visualization via COBRApy
if attempt_cobra and selected_species:
    st.markdown('### Flux visualization (FBA)')
    st.caption('Runs COBRApy FBA with current slider values and optional exchange mapping, then shows top fluxes and a simple pathway flow view.')
    escher_map = st.file_uploader('Optional: upload Escher map JSON to overlay fluxes', type=['json'])
    st.caption('If Plotly is installed, an interactive Sankey will be shown below the table/chart.')
    if st.button('Compute FBA fluxes'):
        res = run_cobra_flux_distribution(model_path_for_cobra, [species_map[k] for k in selected_species], slider_values, reaction_map=exchange_map)
        if res is None:
            st.error('FBA failed (model may lack a solvable objective or mapping).')
        else:
            obj, fluxes, cobra_model = res
            st.success(f'FBA objective: {obj:.4f}')
            rows = flux_table(fluxes, top_n=25)
            if rows:
                st.markdown('#### Top fluxes')
                st.dataframe({'reaction': [r for r, _ in rows], 'flux': [v for _, v in rows]}, use_container_width=True)
            edges = flux_edges(cobra_model, fluxes, top_n=30)
            if edges:
                chart = alt.Chart(alt.Data(values=edges)).mark_line(opacity=0.5).encode(
                    x=alt.X('source:N', title='Reactant'),
                    x2=alt.X2('target:N'),
                    y=alt.value(0),
                    strokeWidth=alt.StrokeWidth('flux:Q', scale=alt.Scale(range=[0.5, 8])),
                    color=alt.Color('direction:N'),
                    tooltip=[
                        alt.Tooltip('reaction:N'),
                        alt.Tooltip('source:N'),
                        alt.Tooltip('target:N'),
                        alt.Tooltip('flux:Q')
                    ]
                ).properties(height=300, width='stretch')
                st.altair_chart(chart)

                fig = plotly_sankey(edges)
                if fig:
                    st.markdown('#### Interactive Sankey')
                    st.plotly_chart(fig, use_container_width=True)

            # Escher map overlay
            if escher_map is not None:
                html = escher_html(escher_map.read(), cobra_model, fluxes)
                if html:
                    st.markdown('#### Escher map')
                    st.components.v1.html(html, height=600, scrolling=True)
                else:
                    st.warning('Could not render Escher map (escher not installed or map invalid).')

# st.markdown('---')
# st.markdown('Notes: This MVP uses mock heuristics for growth and TRY calculations. For realistic optimization you should install `cobra` and map sliders to specific exchange reactions in the model. The upload field accepts drag & drop of SBML/XML model files for non-specialists to try this UI without touching the filesystem.')
