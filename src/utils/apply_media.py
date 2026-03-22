import cobra
import os


def load_and_prep_model(sbml_path):
    """Loads the model and ensures it uses a fast solver."""
    if not os.path.exists(sbml_path):
        raise FileNotFoundError(f"Could not find model at: {sbml_path}")

    print(f"Loading model: {sbml_path}...")
    model = cobra.io.read_sbml_model(sbml_path)
    model.solver = "glpk"
    return model


# ==========================================
# 1. MEDIA SELECTION & GAP-FILLING
# ==========================================
def apply_media_and_gapfill(current_model_path, media, o2_bounds=None):
    print("\n--- STEP 1: Applying Custom Media ---")

    model = load_and_prep_model(str(current_model_path))

    if media is None:
        raise ValueError(
            "media dict is required; provide all exchange bounds from the UI sliders."
        )

    target_medium = model.medium.copy()
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