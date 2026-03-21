# import cobra
# # Load the model (assuming you downloaded yeast-GEM.xml)
# model = cobra.io.read_sbml_model("/Users/taindp/workspace/personal/biox-biohackathon-2026/data/model_Spastorianus_CBS1513.xml")

# # Search for all reactions involving "ergosterol"
# # results = model.metabolites.query("neurospora")
# # for met in results:
# #     print(f"Metabolite: {met.name}, Reactions: {len(met.reactions)}")

# # Search for a specific gene
# gene_ids = model.genes.list_attr("id")
# # print(f"Total genes in the model: {gene_ids}")
# gene = model.genes.get_by_id("SPGP0F01280") # HMG1
# print(f"Reactions for {gene.name}: {gene.reactions}")

import cobra

# 1. Load your drafted SBML model
print("Loading model. This might take a few seconds...")
model = cobra.io.read_sbml_model(
    "/Users/taindp/workspace/personal/biox-biohackathon-2026/data/my_draft_model.xml"
)

# 2. Print the basic stats of your fungus
print("\n--- Model Statistics ---")
print(f"Number of reactions: {len(model.reactions)}")
print(f"Number of metabolites: {len(model.metabolites)}")
print(f"Number of genes: {len(model.genes)}")

# 3. Check the biological objective
print(f"\nCurrent Biological Objective: {model.objective}")

# --- THE FIX IS HERE ---
# Force COBRApy to use the free, unlimited GLPK solver instead of CPLEX
model.solver = "glpk"

print("Opening the floodgates (Unconstraining all nutrients)...")
# Set every single exchange reaction to allow unlimited uptake
for rxn in model.exchanges:
    rxn.lower_bound = -1000.0
# -----------------------

# 4. Run Flux Balance Analysis (FBA)
print("\nRunning Flux Balance Analysis (FBA)...")
solution = model.optimize()

# 5. The Moment of Truth
print("\n--- Phase 1 Results ---")
print(f"Solver Status: {solution.status}")

if solution.objective_value is not None and solution.objective_value > 0.001:
    print(
        f"✅ SUCCESS: Your model grows! Growth Rate: {solution.objective_value:.4f} 1/hr"
    )
else:
    print("❌ FAILED: The model cannot grow (Growth rate is 0.00).")
    print(
        "This means there is a 'gap' in the metabolic network preventing biomass production."
    )
