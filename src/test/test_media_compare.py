import os
import cobra
from typing import Dict, Iterable, Tuple
from cobra.medium import minimal_medium


DEFAULT_MODEL_PATH = (
    "/Users/taindp/workspace/personal/biox-biohackathon-2026/data/"
    "Genome_assembly_ASM18445v3/ncbi_dataset/data/GCA_000184455.3/gem.xml"
)

# Ordered medium entries (uptake bounds, mmol/gDW/h).
BASE_MEDIA: Tuple[Tuple[str, float], ...] = (
    ("EX_glc__D_e", 10.0),
    ("EX_nh4_e", 10.0),
    ("EX_pi_e", 10.0),
    ("EX_so4_e", 3.0),
    ("EX_h2o_e", 1000.0),
    ("EX_h_e", 1000.0),
    ("EX_o2_e", 20.0),
)


def load_model(sbml_path: str) -> cobra.Model:
    if not os.path.exists(sbml_path):
        raise FileNotFoundError(f"Model not found at: {sbml_path}")
    model = cobra.io.read_sbml_model(sbml_path)
    model.solver = "glpk"
    print(f"[info] Objective reaction: {model.objective.expression}")
    return model


def apply_medium(model: cobra.Model, medium: Dict[str, float]):
    exchange_ids = {rxn.id for rxn in model.exchanges}
    filtered = {k: v for k, v in medium.items() if k in exchange_ids}
    missing = set(medium) - exchange_ids
    if missing:
        print(f"[info] Ignoring {len(missing)} entries not in model: {sorted(missing)}")
    print(f"[debug] Applying {len(filtered)} / {len(medium)} medium entries")
    model.medium = filtered


def optimize_growth(model: cobra.Model) -> float:
    sol = model.optimize()
    if sol.status != "optimal":
        print(f"[warn] Optimization status: {sol.status}")
        return 0.0
    return float(sol.objective_value)


def evaluate_all_at_once(model: cobra.Model, medium_items: Iterable[Tuple[str, float]]):
    full_medium = {rxn_id: uptake for rxn_id, uptake in medium_items}
    apply_medium(model, full_medium)
    growth = optimize_growth(model)
    print(f"[all-at-once] growth = {growth:.4f} 1/hr")
    return growth


def evaluate_cumulative_add(
    model: cobra.Model,
    medium_items: Iterable[Tuple[str, float]],
    start_medium: Dict[str, float],
):
    cumulative = start_medium.copy()
    results = []
    for rxn_id, uptake in medium_items:
        cumulative[rxn_id] = uptake
        apply_medium(model, cumulative)
        growth = optimize_growth(model)
        results.append((rxn_id, uptake, growth))
    print("[cumulative add] growth after each addition:")
    for rxn_id, uptake, growth in results:
        print(f" + {rxn_id} @ {uptake}: {growth:.4f} 1/hr")
    return results


if __name__ == "__main__":
    model_path = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
    # start_mode: model | empty | minimal (default uses model's built-in medium)
    start_mode = os.environ.get("START_MEDIUM", "model")
    min_obj = float(os.environ.get("MIN_OBJ", "0.01"))

    model = load_model(model_path)

    if start_mode == "model":
        base = model.medium.copy()
    elif start_mode == "minimal":
        try:
            mm = minimal_medium(model, min_objective_value=min_obj).to_dict()
            print(f"[info] minimal_medium produced {len(mm)} entries for min_obj={min_obj}")
            base = mm
        except Exception as e:
            print(f"[warn] minimal_medium failed: {e}; falling back to empty")
            base = {}
    else:
        base = {}

    # Keep the order deterministic
    medium_items = list(BASE_MEDIA)

    print(f"Using start medium: {start_mode} ({len(base)} entries)")
    print(f"Adding {len(medium_items)} medium components in order\n")

    print("=== All at once ===")
    evaluate_all_at_once(model, medium_items)

    print("\n=== Cumulative add ===")
    evaluate_cumulative_add(model, medium_items, base)
