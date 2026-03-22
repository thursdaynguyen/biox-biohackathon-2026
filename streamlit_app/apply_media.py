import cobra
import os
from pathlib import Path
from typing import Any


def load_and_prep_model(sbml_path: str | os.PathLike[str]) -> cobra.Model:
    """Loads the model from disk and ensures it uses a fast solver."""
    path = Path(sbml_path)
    if not path.exists():
        raise FileNotFoundError(f"Could not find model at: {path}")

    print(f"Loading model: {path}...")
    model = cobra.io.read_sbml_model(path)
    model.solver = "glpk"
    return model


# ==========================================
# 1. MEDIA SELECTION & GAP-FILLING
# ==========================================
def _ensure_model(model_or_path: Any) -> cobra.Model:
    """Return a cobra.Model whether input is a model or a path."""
    if isinstance(model_or_path, cobra.Model):
        return model_or_path
    return load_and_prep_model(str(model_or_path))


def apply_media_and_gapfill(model_or_path: Any, media, o2_bounds=None, merge_with_existing: bool = True) -> cobra.Model:
    """Apply media bounds to a model (path or instance) and return the model.

    - Accepts either a cobra.Model or a path to SBML.
    - merge_with_existing controls whether to start from the current medium or a blank dict.
    """
    print("\n--- STEP 1: Applying Custom Media ---")

    model = _ensure_model(model_or_path)

    if media is None:
        raise ValueError(
            "media dict is required; provide all exchange bounds from the UI sliders."
        )

    base_medium = model.medium.copy() if merge_with_existing else {}
    target_medium = base_medium.copy()
    target_medium.update(media)

    # o2_lower, o2_upper = o2_bounds if o2_bounds else (-20.0, 1000.0)

    # # --- PATCH 1: THE OXYGEN PIPE ---
    # if "EX_o2_e" not in [rxn.id for rxn in model.exchanges]:
    #     print(
    #         " -> [Fix] Oxygen exchange missing! Artificially adding EX_o2_e to the model..."
    #     )
    #     try:
    #         o2_rxn = cobra.Reaction("EX_o2_e")
    #         o2_rxn.name = "O2 exchange"
    #         o2_rxn.lower_bound = o2_lower
    #         o2_rxn.upper_bound = o2_upper
    #         o2_rxn.add_metabolites({model.metabolites.get_by_id("o2_e"): -1.0})
    #         model.add_reactions([o2_rxn])
    #     except KeyError:
    #         print(" -> [Error] 'o2_e' metabolite doesn't exist in this model at all.")

    safe_medium = {}
    model_exchange_ids = [rxn.id for rxn in model.exchanges]

    for rxn_id, bound in target_medium.items():
        if rxn_id in model_exchange_ids:
            safe_medium[rxn_id] = bound
        else:
            print(f" [Warning] Could not find '{rxn_id}' in model. Skipping.")

    model.medium = safe_medium

    sol = model.optimize()
    print(
        f"\nInitial Growth Rate on patched Custom Media: {sol.objective_value:.4f} 1/hr"
    )

    return model

def calculate_byproduct_burden(current_model_path, solution):
    """Sums the total flux of all secreted carbon-containing byproducts."""
    model = load_and_prep_model(str(current_model_path))

    safe_exhaust = ['EX_h2o_e', 'EX_co2_e', 'EX_h_e', 'EX_o2_e']
    total_byproduct_flux = 0.0

    for rxn in model.exchanges:
        flux = solution.fluxes.get(rxn.id, 0.0)
        if flux > 1e-4 and rxn.id not in safe_exhaust:
            total_byproduct_flux += flux
            
    return total_byproduct_flux