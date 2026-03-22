import math
import random
from typing import List, Dict, Tuple, Callable, Optional

# Simple heuristic-based objective and optimizer for MVP.

NUTRIENT_WEIGHTS = {
    'glucose': 5.0,
    'glc': 5.0,
    'sucrose': 3.0,
    'glycerol': 3.0,
    'gln': 2.0,
    'ammonium': 1.5,
    'nh4': 1.5,
    'acetate': 2.0,
    'acet': 2.0,
    'oxygen': 4.0,
    'o2': 4.0,
    'lactate': 1.5,
}

BYPRODUCT_KEYS = [
    'acetate', 'acetic', 'lactate', 'lactic', 'citrate', 'ethanol', 'acetoin', 'formate'
]


def _weight_for_name(name: str) -> float:
    n = name.lower()
    for k, v in NUTRIENT_WEIGHTS.items():
        if k in n:
            return v
    return 0.1


def objective_mock(species_list: List[Dict], values: Dict[str, float]) -> float:
    """Mock objective: weighted sum of log(1+conc) where weights come from heuristics on species names.

    species_list: list of species dicts (from parser) with keys including 'id' and 'name'
    values: mapping from species id -> concentration (float)
    """
    score = 0.0
    for s in species_list:
        sid = s['id']
        name = s.get('name', sid)
        conc = float(values.get(sid, 0.0))
        w = _weight_for_name(name)
        score += w * math.log1p(conc)
    return score


def objective_mock_multi(species_list: List[Dict], values: Dict[str, float],
                         weight_yield: float = 1.0, weight_growth: float = 1.0,
                         weight_byproduct: float = 5.0) -> float:
    """Scalarized multi-objective: growth + yield - byproduct penalty.

    - growth: objective_mock
    - yield: approximated as growth / carbon uptake proxy
    - byproduct penalty: presence of known byproducts in slider set
    """
    growth = objective_mock(species_list, values)
    # carbon uptake proxy: sum of carbon-like sliders
    carbon_keys = ['glucose', 'glc', 'sucrose', 'glycerol']
    carbon = 0.0
    for s in species_list:
        sid = s['id']
        name = s.get('name', '').lower()
        for k in carbon_keys:
            if k in name or k in sid.lower():
                carbon += float(values.get(sid, 0.0))
                break
    carbon = max(carbon, 1e-6)
    yield_proxy = growth / carbon

    # byproduct penalty
    penalty = 0.0
    for s in species_list:
        sid = s['id']
        name = s.get('name', '').lower()
        for k in BYPRODUCT_KEYS:
            if k in name or k in sid.lower():
                penalty += float(values.get(sid, 0.0))
                break

    return weight_growth * growth + weight_yield * yield_proxy - weight_byproduct * penalty


def random_search(species_list: List[Dict], bounds: Dict[str, Tuple[float, float]],
                  objective: Callable[[List[Dict], Dict[str, float]], float],
                  n_iter: int = 200, seed: Optional[int] = None) -> Dict:
    """Random search optimizer over the provided bounds.

    Returns dict with keys: best_score, best_x (mapping id->value), evaluations
    """
    if seed is not None:
        random.seed(seed)
    best = None
    best_x = None
    evals = 0
    for i in range(n_iter):
        x = {}
        for sid, (low, high) in bounds.items():
            x[sid] = random.uniform(low, high)
        score = objective(species_list, x)
        evals += 1
        if best is None or score > best:
            best = score
            best_x = x.copy()
    return {'best_score': best, 'best_x': best_x, 'evaluations': evals}


# Optional: wrapper to attempt COBRApy-based FBA if cobra is installed. This is best-effort.

def try_cobra_fba(sbml_path: str, species_list: List[Dict], values: Dict[str, float], reaction_map: Optional[Dict[str, str]] = None) -> Optional[float]:
    try:
        import cobra
        from cobra.io import read_sbml_model
    except Exception:
        return None

    try:
        model = read_sbml_model(sbml_path)
    except Exception:
        return None

    # Attempt to set exchange reaction bounds by matching species ids or names to metabolites / reactions.
    # reaction_map allows explicit mapping from species id -> exchange reaction id.
    for s in species_list:
        sid = s['id']
        name = s.get('name', '')
        val = float(values.get(sid, 0.0))
        mapped_rid = None
        if reaction_map and sid in reaction_map:
            mapped_rid = reaction_map[sid]

        ex_reactions = []
        if mapped_rid:
            if mapped_rid in model.reactions:
                ex_reactions = [model.reactions.get_by_id(mapped_rid)]

        if not ex_reactions:
            # try find metabolite by id or name
            metabolite = None
            if sid in model.metabolites:
                metabolite = model.metabolites.get_by_id(sid)
            else:
                for m in model.metabolites:
                    if name.lower() in (m.name or '').lower() or sid.lower() in m.id.lower():
                        metabolite = m
                        break
            if metabolite is None:
                continue
            # find exchange reactions involving this metabolite
            ex_reactions = [r for r in model.reactions if metabolite in r.metabolites and r.boundary]
            if not ex_reactions:
                ex_reactions = [r for r in model.reactions if r.id.upper().startswith('EX_') and metabolite in r.metabolites]

        for rxn in ex_reactions:
            try:
                rxn.lower_bound = -abs(val)
            except Exception:
                pass
    try:
        sol = model.optimize()
        if sol.status == 'optimal':
            # return objective value if present
            return float(sol.objective_value)
    except Exception:
        return None
    return None


def run_cobra_flux_distribution(sbml_path: str, species_list: List[Dict], values: Dict[str, float], reaction_map: Optional[Dict[str, str]] = None):
    """Run FBA and return (objective_value, flux_dict, model) or None on failure."""
    try:
        import cobra
        from cobra.io import read_sbml_model
    except Exception:
        return None

    try:
        model = read_sbml_model(sbml_path)
    except Exception:
        return None

    # Apply bounds similarly to try_cobra_fba
    for s in species_list:
        sid = s['id']
        name = s.get('name', '')
        val = float(values.get(sid, 0.0))
        mapped_rid = None
        if reaction_map and sid in reaction_map:
            mapped_rid = reaction_map[sid]

        ex_reactions = []
        if mapped_rid:
            if mapped_rid in model.reactions:
                ex_reactions = [model.reactions.get_by_id(mapped_rid)]

        if not ex_reactions:
            metabolite = None
            if sid in model.metabolites:
                metabolite = model.metabolites.get_by_id(sid)
            else:
                for m in model.metabolites:
                    if name.lower() in (m.name or '').lower() or sid.lower() in m.id.lower():
                        metabolite = m
                        break
            if metabolite is None:
                continue
            ex_reactions = [r for r in model.reactions if metabolite in r.metabolites and r.boundary]
            if not ex_reactions:
                ex_reactions = [r for r in model.reactions if r.id.upper().startswith('EX_') and metabolite in r.metabolites]

        for rxn in ex_reactions:
            try:
                rxn.lower_bound = -abs(val)
            except Exception:
                pass

    try:
        sol = model.optimize()
        if sol.status != 'optimal':
            return None
        fluxes = sol.fluxes.to_dict()
        return float(sol.objective_value), fluxes, model
    except Exception:
        return None
