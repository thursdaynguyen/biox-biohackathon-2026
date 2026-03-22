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

    return {"Titer": titer, "Rate": rate, "Yield": yield_metric}


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
