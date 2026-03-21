from typing import List, Dict, Optional, Tuple
from optimizer import objective_mock


def compute_try(species_list: List[Dict], values: Dict[str, float], product_choice: Optional[str]) -> Tuple[float, float, float]:
    """Compute mock Titer, Rate, Yield.

    Titer: concentration of the chosen product (if given) else 0
    Rate: proxy proportional to mock objective (growth rate proxy)
    Yield: titer divided by sum of major substrates (proxy), clipped
    Returns (titer, rate, yield)
    """
    # Map product id if product_choice is like 'ID - name' or an id
    pid = None
    if product_choice:
        # product_choice may be 'id - name' if coming from selection
        if ' - ' in product_choice:
            pid = product_choice.split(' - ')[0]
        else:
            pid = product_choice
    titer = 0.0
    if pid:
        titer = float(values.get(pid, 0.0))
    # Rate: use objective_mock as proxy
    rate = objective_mock(species_list, values)
    # Identify likely substrates by name heuristics
    substrate_sum = 0.0
    substrate_keys = ['glucose', 'glc', 'glycerol', 'sucrose', 'acetate', 'ammonium', 'nh4']
    for s in species_list:
        sid = s['id']
        name = s.get('name','').lower()
        for k in substrate_keys:
            if k in name or k in sid.lower():
                substrate_sum += float(values.get(sid, 0.0))
                break
    # Avoid divide by zero
    yield_ = titer / (substrate_sum + 1e-6)
    # Normalize yield to typical scale (0-1) by applying a simple sigmoid-like clamp
    if yield_ > 1e3:
        yield_ = 1.0
    return (titer, rate, yield_)
