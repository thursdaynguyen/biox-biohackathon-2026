import os
import datetime
import time
import json
import argparse
import multiprocessing
from functools import partial

import cobra
from cobra.medium import minimal_medium

# We only need the base BlackBoxFacade and Scenario now
from smac import BlackBoxFacade, Scenario
from ConfigSpace import ConfigurationSpace, UniformFloatHyperparameter

def load_and_prep_model(sbml_path):
    """Loads the model, ensures it uses a fast solver, and applies base patches."""
    if not os.path.exists(sbml_path):
        raise FileNotFoundError(f"Could not find model at: {sbml_path}")
        
    print(f"Loading model: {sbml_path}...")
    model = cobra.io.read_sbml_model(sbml_path)
    model.solver = 'glpk'

    # --- PATCH: THE OXYGEN PIPE ---
    if "EX_o2_e" not in [rxn.id for rxn in model.exchanges]:
        try:
            o2_rxn = cobra.Reaction('EX_o2_e')
            o2_rxn.name = 'O2 exchange'
            o2_rxn.lower_bound = -20.0
            o2_rxn.upper_bound = 1000.0
            o2_rxn.add_metabolites({model.metabolites.get_by_id('o2_e'): -1.0})
            model.add_reactions([o2_rxn])
        except KeyError:
            pass
            
    return model

def calculate_survival_recipe(model):
    """Calculates the Lazy Fix auxotrophies ONCE before optimization starts."""
    print("Pre-calculating biological auxotrophies (The Lazy Fix)...")
    with model:
        for rxn in model.exchanges:
            rxn.lower_bound = -10.0 
        try:
            return minimal_medium(model, min_objective_value=0.1).to_dict()
        except Exception as e:
            print(f" -> [Error] Could not calculate survival recipe: {e}")
            return {}

def calculate_byproduct_burden(model, solution):
    """Sums the total flux of all secreted carbon-containing byproducts."""
    safe_exhaust = ['EX_h2o_e', 'EX_co2_e', 'EX_h_e', 'EX_o2_e']
    total_byproduct_flux = 0.0

    for rxn in model.exchanges:
        flux = solution.fluxes.get(rxn.id, 0.0)
        if flux > 1e-4 and rxn.id not in safe_exhaust:
            total_byproduct_flux += flux
            
    return total_byproduct_flux

def objective_function(config, seed, model, survival_recipe, base_medium):
    """
    Evaluates a specific media formulation and returns a fitness score.

    The candidate medium overlays on top of the GEM's native medium so we keep
    any rich defaults encoded in the SBML rather than starting from scratch.
    """
    EX_glc__D_e = float(config["EX_glc__D_e"]) 
    EX_nh4_e = float(config["EX_nh4_e"]) 
    EX_pi_e = float(config["EX_pi_e"]) 
    EX_so4_e = float(config["EX_so4_e"]) 
    EX_o2_e = float(config["EX_o2_e"]) 
    EX_xyl__D_e = float(config["EX_xyl__D_e"]) 
    EX_glyc_e = float(config["EX_glyc_e"]) 
    EX_cellb_e = float(config["EX_cellb_e"]) 

    target_media = base_medium.copy()
    target_media.update({
        'EX_glc__D_e': EX_glc__D_e, 'EX_nh4_e': EX_nh4_e,
        'EX_pi_e': EX_pi_e,         'EX_so4_e': EX_so4_e,
        'EX_o2_e': EX_o2_e,         'EX_xyl__D_e': EX_xyl__D_e,
        'EX_glyc_e': EX_glyc_e,     'EX_cellb_e': EX_cellb_e
    })

    # Auto-inject the survival recipe
    for rxn_id, required_flux in survival_recipe.items():
        if rxn_id not in target_media:
            target_media[rxn_id] = required_flux

    safe_medium = {k: v for k, v in target_media.items() if k in [rxn.id for rxn in model.exchanges]}

    with model:
        model.medium = safe_medium
        sol = model.optimize()

        # Base Growth Check
        # if sol.status != 'optimal' or sol.objective_value < 0.01:
        #     return 1000.0  

        growth_rate = sol.objective_value
        byproduct_flux = calculate_byproduct_burden(model, sol)

        total_carbon_cost = (abs(EX_glc__D_e) * 6) + \
                            (abs(EX_xyl__D_e) * 5) + \
                            (abs(EX_glyc_e) * 3) + \
                            (abs(EX_cellb_e) * 12)

        W_GROWTH = 10.0      
        W_BYPRODUCT = 2.0    
        W_COST = 0.5         

        print(f" -> Growth: {growth_rate:.4f}, Byproduct Flux: {byproduct_flux:.4f}, Carbon Cost: {total_carbon_cost:.2f}")

        fitness_score = (growth_rate * W_GROWTH) - (byproduct_flux * W_BYPRODUCT) - (total_carbon_cost * W_COST)

        # SMAC ALWAYS minimizes, so we return the negative fitness score
        return -fitness_score

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(description="SMAC3 Naive Media Optimization")
    argparser.add_argument("--total-trials", type=int, default=500, help="Total number of media recipes to test")
    argparser.add_argument("--total-cpus", type=int, default=multiprocessing.cpu_count())
    argparser.add_argument("--gem-fpath", type=str, required=True, help="Path to the GEM file")
    args = argparser.parse_args()

    # 1. Global Pre-computation
    master_model = load_and_prep_model(args.gem_fpath)
    base_medium = master_model.medium.copy()  # Preserve any rich medium encoded in the GEM
    base_survival_recipe = calculate_survival_recipe(master_model)

    # 2. Define Search Space
    cs = ConfigurationSpace()
    cs.add_hyperparameters([
        UniformFloatHyperparameter("EX_glc__D_e", lower=-15.0, upper=-0.1),
        UniformFloatHyperparameter("EX_nh4_e", lower=-15.0, upper=-0.1),
        UniformFloatHyperparameter("EX_pi_e", lower=-15.0, upper=-0.1),
        UniformFloatHyperparameter("EX_so4_e", lower=-15.0, upper=-0.1),
        UniformFloatHyperparameter("EX_o2_e", lower=-15.0, upper=-0.1),
        UniformFloatHyperparameter("EX_xyl__D_e", lower=-15.0, upper=-0.1),
        UniformFloatHyperparameter("EX_glyc_e", lower=-15.0, upper=-0.1),
        UniformFloatHyperparameter("EX_cellb_e", lower=-15.0, upper=-0.1),
    ])

    # 3. Clean, Budget-Free Scenario
    out_dir = os.path.join(os.path.dirname(os.path.abspath(args.gem_fpath)), "smac3")
    scenario = Scenario(
        configspace=cs,
        deterministic=True,
        n_trials=args.total_trials,  # Just exactly how many total combinations to guess
        output_directory=out_dir,
        n_workers=max(1, args.total_cpus)
    )

    # 4. Bind the model and recipe to the objective function
    target_function = partial(
        objective_function,
        model=master_model,
        survival_recipe=base_survival_recipe,
        base_medium=base_medium,
    )

    # 5. Run standard BlackBox Optimization
    print("\n🚀 Initiating Naive Bayesian Optimizer...")
    start_time = time.time()
    
    smac = BlackBoxFacade(
        scenario,
        target_function,
        overwrite=True
    )

    incumbent = smac.optimize()
    elapsed_time = time.time() - start_time

    # 6. Save Best Config
    best_config = incumbent.get_dictionary()
    best_cost = smac.runhistory.get_cost(incumbent)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs(out_dir, exist_ok=True)
    data = {
        "best_config": best_config,
        "best_fitness_score": best_cost, # Reverse it back so it makes sense to humans
        "elapsed_time_seconds": elapsed_time,
    }
    with open(os.path.join(out_dir, f"{timestamp}.json"), "w") as f:
        json.dump(data, f, indent=4)

    print(f"\n✅ Optimization Complete in {elapsed_time:.1f} seconds!")
    print(f"Best Configuration: {best_config}")
    print(f"Maximized Fitness Score: {best_cost:.4f}")