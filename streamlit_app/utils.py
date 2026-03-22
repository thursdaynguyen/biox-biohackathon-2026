from typing import Dict, Optional, Tuple
from apply_media import load_and_prep_model, apply_media_and_gapfill


def compute_try(
    values: Dict[str, float],
    product_choice: Optional[str],
    model_path: str,
    carbon_source: str = 'EX_glc__D_e',
    sim_time_h: float = 24.0,
    initial_biomass: float = 0.5,
) -> Tuple[float, float, float]:
    """Compute TRY metrics using the current SBML model and UI media.

    - Loads the model via load_and_prep_model
    - Applies slider media via apply_media_and_gapfill
    - Mirrors evaluate_TRY_metrics for rate, yield, titer
    Returns (titer, rate, yield_). On any failure, returns zeros.
    """
    try:
        model = load_and_prep_model(model_path)
        base_medium = model.medium.copy()
    except Exception:
        return (0.0, 0.0, 0.0)

    # Apply media from slider values (treated as exchange bounds)
    try:
        model.medium = base_medium.copy()
        apply_media_and_gapfill(model, media=values, merge_with_existing=False)
    except Exception:
        return (0.0, 0.0, 0.0)

    pid = None
    if product_choice:
        pid = product_choice.split(' - ')[0] if ' - ' in product_choice else product_choice
    if not pid:
        return (0.0, 0.0, 0.0)

    solution = model.optimize()
    if solution.status != 'optimal' or solution.objective_value < 1e-6:
        return (0.0, 0.0, 0.0)

    if pid not in [rxn.id for rxn in model.reactions]:
        return (0.0, 0.0, 0.0)

    rate = float(solution.fluxes.get(pid, 0.0))
    carbon_flux = float(solution.fluxes.get(carbon_source, 0.0))
    yield_metric = abs(rate / carbon_flux) if carbon_flux < -1e-6 else 0.0
    titer = rate * initial_biomass * sim_time_h

    return (titer, rate, yield_metric)


def compute_growth_score(values: Dict[str, float], model_path: str) -> float:
    """Compute growth score using the model objective after applying media.

    Loads the model fresh each call to ensure slider changes are reflected immediately.
    Returns objective value (biomass) or 0.0 on failure.
    """
    model = load_and_prep_model(model_path)
    base_medium = model.medium.copy()

    model.medium = base_medium.copy()
    apply_media_and_gapfill(model, media=values)
    solution = model.optimize()

    objective_val = float(solution.objective_value)
    return objective_val if objective_val > 1e-9 else 0.0
