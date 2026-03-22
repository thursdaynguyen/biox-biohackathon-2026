import xml.etree.ElementTree as ET
from typing import List, Dict

SBML_NS = "http://www.sbml.org/sbml/level3/version1/core"

def _ns(tag: str) -> str:
    return f"{{{SBML_NS}}}{tag}"


def parse_sbml_extracellular(path: str) -> List[Dict]:
    """Parse an SBML file and return a list of extracellular species.

    Each dict contains: id, name, compartment, boundaryCondition (bool), formula (if present)
    """
    tree = ET.parse(path)
    root = tree.getroot()
    species_e = []
    for species in root.findall(f".//{_ns('species')}"):
        sid = species.get('id')
        name = species.get('name') or sid
        compartment = species.get('compartment') or ''
        boundary = species.get('boundaryCondition')
        boundary_bool = (boundary == 'true') if boundary is not None else False
        formula = species.get('{http://www.sbml.org/sbml/level3/version1/fbc/version2}chemicalFormula')

        # Heuristic: extracellular compartment often ends with _e or named 'extracellular'
        if compartment.endswith('_e') or compartment.lower().endswith('e') or 'extracellular' in compartment.lower() or boundary_bool:
            species_e.append({
                'id': sid,
                'name': name,
                'compartment': compartment,
                'boundaryCondition': boundary_bool,
                'formula': formula
            })
    return species_e


if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        items = parse_sbml_extracellular(sys.argv[1])
        for s in items[:50]:
            print(s)
