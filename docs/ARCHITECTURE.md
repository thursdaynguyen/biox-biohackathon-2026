# Architecture Notes

- **Intake**: EggNOG-mapper annotations + CarveFungi with fungal/eukaryotic universal template and biomass; outputs compartmentalized SBML.
- **Curation**: Optional gap-fill against minimal C/N/P/S + trace metals to ensure mu > 0.
- **Engine**: pFBA with oxygen unconstrained; objective defaults to biomass.
- **Pruning**: Shadow prices filter non-limiting nutrients; compute and flag C/N ratio.
- **Benchmarking**: Expose mu_max, Y_X/S, and optional titers for target metabolites.

APIs:
- `/upload`: genome upload → full pipeline run.
- `/simulate`: run from existing SBML model.

Open design items:
- Media definitions for filamentous fungi.
- Ergosterol/chitin biomass coefficients validation.
- Secondary metabolism coverage and overflow metabolism handling.
