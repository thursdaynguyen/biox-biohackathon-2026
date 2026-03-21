import cobra
import os
from cobra.flux_analysis import gapfilling


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
from cobra.medium import minimal_medium


def apply_media_and_gapfill(model, media_type):
    print(f"\n--- STEP 1: Applying {media_type} Media (The Lazy Way) ---")

    # --- PATCH 1: THE OXYGEN PIPE ---
    if "EX_o2_e" not in [rxn.id for rxn in model.exchanges]:
        try:
            o2_rxn = cobra.Reaction("EX_o2_e")
            o2_rxn.name = "O2 exchange"
            o2_rxn.lower_bound = -20.0
            o2_rxn.upper_bound = 1000.0
            o2_rxn.add_metabolites({model.metabolites.get_by_id("o2_e"): -1.0})
            model.add_reactions([o2_rxn])
        except KeyError:
            pass

    # --- STEP A: CALCULATE THE SURVIVAL RECIPE ---
    print(" -> Dynamically calculating missing required nutrients...")

    # We use a 'with' block so we don't permanently alter the model yet
    with model:
        for rxn in model.exchanges:
            rxn.lower_bound = -10.0  # Open floodgates

        # Force the model to grow to find out what it eats
        try:
            # model.reactions.Growth.lower_bound = 0.1
            survival_recipe = minimal_medium(model, min_objective_value=0.1).to_dict()
        except Exception as e:
            print(f" -> [Error] Could not calculate survival recipe: {e}")
            survival_recipe = {}

    # --- STEP B: DEFINE YOUR BASE MEDIA ---
    base_media = {
        "EX_glc__D_e": 10.0,  # Primary Carbon
        "EX_nh4_e": -5.0,  # Primary Nitrogen
        "EX_pi_e": 3.0,
        "EX_so4_e": 3.0,
        "EX_h2o_e": 1000.0,
        "EX_h_e": 1000.0,
        "EX_o2_e": 1000.0,
    }

    if media_type == "Complex":
        yeast_extract_proxy = {
            "EX_ala__L_e": 2.0,
            "EX_arg__L_e": 2.0,
            "EX_asn__L_e": 2.0,
            "EX_asp__L_e": 2.0,
            "EX_cys__L_e": 2.0,
            "EX_glu__L_e": 2.0,
            "EX_gln__L_e": 2.0,
            "EX_gly_e": 2.0,
            "EX_his__L_e": 2.0,
            "EX_ile__L_e": 2.0,
            "EX_leu__L_e": 2.0,
            "EX_lys__L_e": 2.0,
            "EX_met__L_e": 2.0,
            "EX_phe__L_e": 2.0,
            "EX_pro__L_e": 2.0,
            "EX_ser__L_e": 2.0,
            "EX_thr__L_e": 2.0,
            "EX_trp__L_e": 2.0,
            "EX_tyr__L_e": 2.0,
            "EX_val__L_e": 2.0,
        }
        base_media.update(yeast_extract_proxy)

    # --- STEP C: THE LAZY MERGE ---
    # We take your base media, and inject whatever the model demands to survive
    final_media = base_media.copy()

    for rxn_id, required_flux in survival_recipe.items():
        # Only inject the nutrient if it's not already in our media
        if rxn_id not in final_media:
            final_media[rxn_id] = required_flux
            print(f"    [Lazy Fix] Auto-injected: {rxn_id} ({required_flux:.4f})")

    # --- STEP D: APPLY SAFELY ---
    safe_medium = {}
    model_exchange_ids = [rxn.id for rxn in model.exchanges]

    for rxn_id, bound in final_media.items():
        if rxn_id in model_exchange_ids:
            safe_medium[rxn_id] = bound

    model.medium = safe_medium

    sol = model.optimize()
    print(
        f"\n✅ Initial Growth Rate on Auto-Supplemented {media_type} Media: {sol.objective_value:.4f} 1/hr"
    )

    return model


# ==========================================
# 2. NUTRIENT SWAPPING (SHADOW PRICES)
# ==========================================
def evaluate_shadow_prices(model):
    print("\n--- STEP 2: Evaluating Shadow Prices (Nutrient Bottlenecks) ---")
    solution = model.optimize()

    if solution.status != "optimal" or solution.objective_value < 1e-6:
        print("Cannot evaluate shadow prices; model is starving/not optimal.")
        return

    extracellular_mets = [m for m in model.metabolites if m.id.endswith("_e")]

    suggestions = []
    for met in extracellular_mets:
        price = solution.shadow_prices.get(met.id, 0)
        if price < -0.01:
            suggestions.append(
                {"metabolite": met.name, "id": met.id, "value": abs(price)}
            )

    if not suggestions:
        print("No immediate nutrient bottlenecks found.")
        return

    suggestions = sorted(suggestions, key=lambda x: x["value"], reverse=True)

    print("Top 5 High-Value Nutrient Suggestions to boost growth:")
    for item in suggestions[:5]:
        print(f" -> Add {item['metabolite']} (Value/Impact: {item['value']:.4f})")


# ==========================================
# 3. C:N RATIO TUNING
# ==========================================
def calculate_and_tune_CN_ratio(model, target_ratio=10.0):
    print(f"\n--- STEP 3: C:N Ratio Tuning (Target = {target_ratio}) ---")
    total_c_uptake = 0.0
    total_n_uptake = 0.0

    solution = model.optimize()

    for rxn in model.exchanges:
        flux = solution.fluxes[rxn.id]
        if flux < -1e-6:  # It is being consumed
            met = list(rxn.metabolites.keys())[0]
            elements = met.elements
            c_atoms = elements.get("C", 0)
            n_atoms = elements.get("N", 0)

            total_c_uptake += c_atoms * abs(flux)
            total_n_uptake += n_atoms * abs(flux)

    current_ratio = (
        total_c_uptake / total_n_uptake if total_n_uptake > 0 else float("inf")
    )
    print(
        f"Current Elemental Uptake -> Carbon: {total_c_uptake:.2f}, Nitrogen: {total_n_uptake:.2f}"
    )
    print(f"Current C:N Ratio: {current_ratio:.2f}")

    if current_ratio < target_ratio and "EX_nh4_e" in [
        rxn.id for rxn in model.reactions
    ]:
        print(f"Action: Shifting to Nitrogen limitation to reach C:N {target_ratio}")
        model.reactions.EX_nh4_e.lower_bound = -(total_c_uptake / target_ratio)
        print(
            f" -> New EX_nh4_e bound set to: {model.reactions.EX_nh4_e.lower_bound:.2f}"
        )


# ==========================================
# 4. TRY METRICS (Titer, Rate, Yield)
# ==========================================
def evaluate_TRY_metrics(
    model,
    target_product="EX_cit_e",
    carbon_source="EX_glc__D_e",
    sim_time_h=24.0,
    initial_biomass=0.5,
):
    """Calculates Industrial Titer, Rate, and Yield."""
    print(f"\n--- STEP 4: Evaluating TRY Metrics (Target: {target_product}) ---")
    solution = model.optimize()

    # Safety check: Is the model actually growing/functioning?
    if solution.status != "optimal" or solution.objective_value < 1e-6:
        print(" [Error] Model is not growing. All metrics are 0.0")
        return {"Rate": 0.0, "Yield": 0.0, "Titer": 0.0}

    # Safety check: Does the target product exist in this model's database?
    if target_product not in [rxn.id for rxn in model.reactions]:
        print(
            f" [Warning] Product '{target_product}' not found in model. Is there a typo?"
        )
        return {"Rate": 0.0, "Yield": 0.0, "Titer": 0.0}

    # 1. RATE (Specific Productivity: mmol/gDW/h)
    # A positive flux means it is being secreted out of the cell
    rate = solution.fluxes.get(target_product, 0.0)

    # 2. YIELD (Efficiency: moles of product / moles of carbon consumed)
    carbon_flux = solution.fluxes.get(carbon_source, 0.0)
    if carbon_flux < -1e-6:
        yield_metric = abs(rate / carbon_flux)
    else:
        yield_metric = 0.0

    # 3. TITER (Concentration: mmol/L)
    # Since standard FBA has no time/volume, we approximate: Rate * Biomass * Time
    titer = rate * initial_biomass * sim_time_h

    print(f" -> Rate (Productivity): {rate:.4f} mmol/gDW/h")
    print(f" -> Yield (Efficiency):  {yield_metric:.4f} mol product / mol carbon")
    print(f" -> Titer (Estimated):   {titer:.4f} mmol/L (after {sim_time_h}h)")

    return {"Rate": rate, "Yield": yield_metric, "Titer": titer}


# ==========================================
# 5. EVOLUTIONARY ALGORITHM FITNESS SCORE
# ==========================================
def calculate_fitness_score(metrics, yield_weight=0.7, rate_weight=0.3):
    """
    Combines the conflicting TRY metrics into a single numerical score
    for your optimization algorithms to judge.
    """
    print("\n--- STEP 5: Calculating EA Fitness Score ---")

    # Normalize or scale metrics if needed, but simple addition works for baselines
    fitness = (metrics["Yield"] * yield_weight) + (metrics["Rate"] * rate_weight)

    print(f" -> Yield Weight: {yield_weight*100}% | Rate Weight: {rate_weight*100}%")
    print(f" -> FINAL FITNESS SCORE: {fitness:.4f}")

    return fitness


# ==========================================
# MAIN EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    MODEL_PATH = "/Users/taindp/workspace/personal/biox-biohackathon-2026/data/out.cleaned.xml"  # <-- UPDATE THIS PATH TO YOUR DRAFT SBML MODEL

    try:
        fungal_model = load_and_prep_model(MODEL_PATH)

        # NOTE: Changing to 'Complex' here just so you can actually see the TRY math work,
        # since we know Minimal currently results in a 0.00 growth rate!
        fungal_model = apply_media_and_gapfill(fungal_model, media_type="Minimal")

        evaluate_shadow_prices(fungal_model)

        calculate_and_tune_CN_ratio(fungal_model, target_ratio=20.0)

        print(f"\n--- FINAL CHECK ---")
        final_sol = fungal_model.optimize()
        print(f"Post-Tuning Growth Rate: {final_sol.objective_value:.4f} 1/hr")

        # Run the new Modules
        # Ensure you replace 'EX_cit_e' with the exact BiGG ID of your specialist's product!
        # try_metrics = evaluate_TRY_metrics(fungal_model, target_product='EX_cit_e', carbon_source='EX_glc__D_e')

        # final_score = calculate_fitness_score(try_metrics, yield_weight=0.7, rate_weight=0.3)

    except FileNotFoundError as e:
        print(f"\n[ERROR]: {e}")
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR]: {e}")
