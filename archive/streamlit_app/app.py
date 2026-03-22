import os
import io
import streamlit as st
import altair as alt
from typing import Dict, Tuple, List
from parser import parse_sbml_extracellular
from optimizer import objective_mock, objective_mock_multi, random_search, try_cobra_fba, run_cobra_flux_distribution
from utils import compute_try
from gem_builder import build_gem_from_genome, GEMBuildError
from flux_viz import flux_table, flux_edges, escher_html, plotly_sankey

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

MODELS_DIR = os.path.dirname(__file__)

st.set_page_config(page_title="MVP Media Optimizer", layout='wide')
st.title('MVP Media/Conditions Optimizer')

# Sidebar: model selection or upload
st.sidebar.header('Model selection')
sbml_files = [f for f in os.listdir(MODELS_DIR) if f.lower().endswith('.xml') or f.lower().endswith('.sbml')]

st.sidebar.subheader('Upload genome (FASTA/GBK) to auto-build GEM')
genome_upload = st.sidebar.file_uploader('Drag & drop genome file', type=['fasta', 'fa', 'fna', 'faa', 'gbk', 'gb'])

st.sidebar.subheader('Or upload SBML directly')
uploaded = st.sidebar.file_uploader('SBML/XML file', type=['xml', 'sbml'])

use_uploaded = uploaded is not None
use_genome = genome_upload is not None
model_data = None
model_path = None

if use_genome:
    st.sidebar.info('Genome upload detected; will attempt to build GEM via CarveMe if available.')
    model_data = genome_upload.read()
elif use_uploaded:
    st.sidebar.success('Using uploaded SBML/XML (session-only)')
    model_data = uploaded.read()
else:
    if not sbml_files:
        st.sidebar.warning('No SBML/XML model files found in the project folder.')
        st.stop()
    selected = st.sidebar.selectbox('Choose a model file', sbml_files)
    model_path = os.path.join(MODELS_DIR, selected)

st.sidebar.markdown('---')
st.sidebar.header('Optimizer settings')
objective_choice = st.sidebar.selectbox('Objective', ['Mock growth', 'Mock product', 'TRY (titer/rate/yield)', 'Growth+Yield - Byproducts'])
n_iter = int(st.sidebar.number_input('Random search iterations', min_value=10, max_value=5000, value=500))
attempt_cobra = st.sidebar.checkbox('Attempt COBRApy-based FBA if available', value=False)
st.sidebar.markdown('---')
st.sidebar.subheader('Weights (for multi-objective)')
weight_growth = float(st.sidebar.number_input('Weight: growth', value=1.0, step=0.1))
weight_yield = float(st.sidebar.number_input('Weight: yield', value=1.0, step=0.1))
weight_byprod = float(st.sidebar.number_input('Weight: byproduct penalty', value=5.0, step=0.5))

# Build GEM if genome provided, else parse existing SBML
with st.spinner('Loading / building model...'):
    if use_genome:
        try:
            tmp_path = build_gem_from_genome(model_data, genome_upload.name)
            model_path_for_cobra = tmp_path
            species_e = parse_sbml_extracellular(tmp_path)
            st.sidebar.success('GEM built from genome (CarveMe).')
        except GEMBuildError as e:
            st.error(f'GEM build failed: {e}')
            st.stop()
    elif use_uploaded:
        import tempfile
        fd, tmp_path = tempfile.mkstemp(suffix='.xml')
        with os.fdopen(fd, 'wb') as f:
            f.write(model_data)
        species_e = parse_sbml_extracellular(tmp_path)
        model_path_for_cobra = tmp_path
    else:
        species_e = parse_sbml_extracellular(model_path)
        model_path_for_cobra = model_path

st.markdown(f'**Found {len(species_e)} extracellular species** (heuristic).')

# Restrict selection to the fixed set of exchange reactions with friendly display names
species_lookup = {s['id']: s for s in species_e}
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

    # exact candidate match
    for cid in candidates:
        if cid in species_lookup:
            matched_id = cid
            base = species_lookup[cid]
            break

    # heuristic: strip EX_ prefix if present and try again
    if base is None and desired_id.lower().startswith('ex_'):
        stripped = desired_id[3:]
        if stripped in species_lookup:
            matched_id = stripped
            base = species_lookup[stripped]

    # heuristic: case-insensitive contains match
    if base is None:
        target = desired_id.lower()
        for sid, sdata in species_lookup.items():
            if target == sid.lower() or target in sid.lower():
                matched_id = sid
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
            min_v = cols[0].number_input(f'{friendly_label} min', value=0.0, step=0.1, key=f'{sid}_min')
            max_v = cols[1].number_input(f'{friendly_label} max', value=100.0, step=0.1, key=f'{sid}_max')
            default_v = cols[2].number_input(f'{friendly_label} default', value=10.0, step=0.1, key=f'{sid}_def')
            # sanitize
            if max_v < min_v:
                max_v = min_v
            bounds[sid] = (float(min_v), float(max_v))
            default_vals[sid] = float(default_v)
    else:
        st.info('Pick some species to customize slider bounds.')

st.markdown('### Live sliders')
slider_values: Dict[str, float] = {}
if selected_species:
    cols = st.columns(2)
    for i, key in enumerate(selected_species):
        s = species_map[key]
        col = cols[i % len(cols)]
        sid = s['id']
        lo, hi = bounds.get(sid, (0.0, 100.0))
        friendly_label = species_display.get(sid, s.get('name', sid))
        val = col.slider(friendly_label, min_value=lo, max_value=hi, value=default_vals.get(sid, (lo+hi)/2), step=max((hi-lo)/100.0, 0.01), key=sid)
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
    if objective_choice == 'Mock growth':
        score = objective_mock([species_map[f] for f in selected_species], slider_values)
        st.metric('Mock growth score', f"{score:.3f}")
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
product_choice = None
if objective_choice in ['Mock product', 'TRY (titer/rate/yield)']:
    product_options = ['-- none --'] + selected_species
    product_choice = st.selectbox(
        'Select product species (for titer/rate/yield calculations)',
        product_options,
        format_func=lambda sid: species_display.get(sid, sid) if sid != '-- none --' else '-- none --'
    )

if run_opt:
    if not selected_species:
        st.warning('Pick at least one species to optimize.')
    else:
        # Build bounds
        if not bounds:
            bounds = {species_map[k]['id']:(0.0, 100.0) for k in selected_species}

        # Choose objective function wrapper
        def eval_objective(species_list: List[dict], x: Dict[str, float]) -> float:
            # If COBRA requested and available, try to get FBA objective
            if attempt_cobra:
                fba_val = try_cobra_fba(model_path_for_cobra, species_list, x, reaction_map=exchange_map)
                if fba_val is not None:
                    return fba_val
            # Fallbacks
            if objective_choice == 'Mock growth':
                return objective_mock(species_list, x)
            elif objective_choice == 'Mock product':
                # maximize product conc
                if product_choice and product_choice != '-- none --':
                    pid = species_map[product_choice]['id']
                    return float(x.get(pid, 0.0))
                return objective_mock(species_list, x)
            elif objective_choice == 'Growth+Yield - Byproducts':
                return objective_mock_multi(species_list, x, weight_yield=weight_yield,
                                            weight_growth=weight_growth, weight_byproduct=weight_byprod)
            else:
                # TRY: combine titer and rate as a single scalar (mock)
                t, r, y = compute_try(species_list, x, product_choice if product_choice != '-- none --' else None)
                # combine with weights: prioritize yield then titer then rate
                return float(y * 100.0 + t * 0.1 + r * 0.01)

        with st.spinner('Searching...'):
            res = random_search([species_map[k] for k in selected_species], bounds, eval_objective, n_iter=n_iter)

        st.success(f"Best score: {res['best_score']:.3f} after {res['evaluations']} evaluations")
        st.subheader('Suggested settings')
        for sid, val in res['best_x'].items():
            st.write(f"{sid}: {val:.3f}")

        # Compute TRY metrics for best found
        titer, rate, yield_ = compute_try([species_map[k] for k in selected_species], res['best_x'], product_choice if product_choice and product_choice != '-- none --' else None)
        st.markdown('#### Mock TRY for suggested settings')
        st.metric('Titer (mock)', f"{titer:.4f}")
        st.metric('Rate (mock)', f"{rate:.4f}")
        st.metric('Yield (mock)', f"{yield_:.4f}")

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

st.markdown('---')
st.markdown('Notes: This MVP uses mock heuristics for growth and TRY calculations. For realistic optimization you should install `cobra` and map sliders to specific exchange reactions in the model. The upload field accepts drag & drop of SBML/XML model files for non-specialists to try this UI without touching the filesystem.')
