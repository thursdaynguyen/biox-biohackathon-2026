import cobra
from cobra.medium import minimal_medium

print("Loading model...")
model = cobra.io.read_sbml_model(
    "/Users/taindp/workspace/personal/biox-biohackathon-2026/data/my_draft_model.xml"
)
model.solver = "glpk"

# 1. Open the floodgates (allow it to eat anything at a rate of 10)
for rxn in model.exchanges:
    rxn.lower_bound = -10.0

# 2. Force the model to grow! (Your previous output showed the objective is named 'Growth')
try:
    model.reactions.Growth.lower_bound = 0.1
except KeyError:
    print(
        "Could not find a reaction named 'Growth'. Please check the exact biomass ID."
    )

print("\nCalculating the optimal custom media formulation...")

# 3. Run the Minimal Medium algorithm
try:
    optimal_media = minimal_medium(model, min_objective_value=0.1)

    print("\n✅ SUCCESS! Here is the exact 'Custom Media' your model requires to grow:")
    print("-" * 60)
    print(f"{'Exchange ID':<20} | {'Flux':<10} | {'Metabolite Name'}")
    print("-" * 60)

    for rxn_id, flux in optimal_media.items():
        # Get the actual name of the metabolite for readability
        met_name = list(model.reactions.get_by_id(rxn_id).metabolites.keys())[0].name
        print(f"{rxn_id:<20} | {flux:<10.4f} | {met_name}")

except Exception as e:
    print(f"\n❌ FAILED to calculate minimal medium. Error: {e}")
