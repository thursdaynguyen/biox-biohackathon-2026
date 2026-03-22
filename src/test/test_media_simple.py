import os
import cobra


# DEFAULT_MODEL_PATH = (
#     "/Users/taindp/workspace/personal/biox-biohackathon-2026/data/MG1655/"
#     "ncbi_dataset/data/GCA_000005845.2/gem.xml"
# )

DEFAULT_MODEL_PATH = (
    "/Users/taindp/workspace/personal/biox-biohackathon-2026/data/Genome_assembly_ASM18445v3/ncbi_dataset/data/GCA_000184455.3/gem.xml"
)

# Baseline media candidates. Values are allowed uptake rates (mmol/gDW/h).
BASE_MEDIA = {
    "EX_glc__D_e": 10.0,
    # "EX_nh4_e": 10.0,
    # "EX_pi_e": 10.0,
    # "EX_so4_e": 3.0,
    # "EX_h2o_e": 1000.0,
    # "EX_h_e": 1000.0,
    # "EX_o2_e": 20.0,
}


def load_model(sbml_path: str):
    """Load SBML model with a deterministic solver."""
    if not os.path.exists(sbml_path):
        raise FileNotFoundError(f"Model not found at: {sbml_path}")

    model = cobra.io.read_sbml_model(sbml_path)
    model.solver = "glpk"
    return model


def apply_medium(model: cobra.Model, medium: dict):
    """Apply a medium dictionary but only for exchanges present in the model."""
    exchange_ids = {rxn.id for rxn in model.exchanges}
    filtered = {k: v for k, v in medium.items() if k in exchange_ids}
    missing = set(medium) - exchange_ids
    if missing:
        print(f"[info] Ignoring {len(missing)} medium entries not in model: {sorted(missing)}")

    model.medium = filtered


def evaluate_media_components(model: cobra.Model, medium: dict):
    """Report growth with full medium and with each component removed.

    Uses the model's current medium as baseline and overlays the provided medium
    entries so we inherit any rich defaults from the SBML file.
    """

    base = model.medium.copy()
    merged = base.copy()
    merged.update(medium)

    apply_medium(model, merged)
    baseline = model.optimize()
    print(f"Baseline growth (baseline+supplied): {baseline.objective_value:.4f} 1/hr")

    results = []
    for rxn_id in medium:
        test_medium = merged.copy()
        test_medium[rxn_id] = 0.0
        apply_medium(model, test_medium)
        sol = model.optimize()
        growth = sol.objective_value if sol.status == "optimal" else 0.0
        results.append((rxn_id, growth))

    # Restore merged baseline for any further work
    apply_medium(model, merged)

    print("\nGrowth after removing each component:")
    for rxn_id, growth in results:
        delta = baseline.objective_value - growth
        print(f" - {rxn_id}: {growth:.4f} (delta: {delta:.4f})")


if __name__ == "__main__":
    model_path = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
    model = load_model(model_path)
    evaluate_media_components(model, BASE_MEDIA)

    # import cobra
    # import pandas as pd

    # model = cobra.io.read_sbml_model(DEFAULT_MODEL_PATH)
    # model.solver = "glpk"  # Force use of GLPK to avoid CPLEX licensing issues

    # # Example nutrients to add one-by-one (uptake rates are positive here for model.medium)
    # candidates = {
    #     "EX_glc__D_e": 10.0,
    #     # "EX_o2_e": 20.0,
    #     # "EX_nh4_e": 10.0,
    #     # "EX_pi_e": 10.0,
    # }

    # results = []

    # # Start from current medium
    # base_medium = model.medium.copy()

    # for rxn_id, uptake in candidates.items():
    #     with model:  # temporary changes per iteration
    #         med = base_medium.copy()
    #         med[rxn_id] = uptake   # add this nutrient
    #         model.medium = med

    #         sol = model.optimize()
    #         results.append({
    #             "added": rxn_id,
    #             "uptake": uptake,
    #             "status": sol.status,
    #             "objective": sol.objective_value,
    #         })

    # df = pd.DataFrame(results).sort_values("objective", ascending=False)
    # print(df)
