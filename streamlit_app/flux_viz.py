from typing import Dict, List, Tuple, Optional


def flux_table(fluxes: Dict[str, float], top_n: int = 25, min_abs_flux: float = 1e-6) -> List[Tuple[str, float]]:
    items = [(rid, v) for rid, v in fluxes.items() if abs(v) >= min_abs_flux]
    items.sort(key=lambda x: abs(x[1]), reverse=True)
    return items[:top_n]


def flux_edges(model, fluxes: Dict[str, float], top_n: int = 30, min_abs_flux: float = 1e-6):
    """Build edge list for Sankey-like visualization: reactant -> product with weight.

    We split flux magnitude equally across reactant-product pairs to keep it simple.
    """
    # Select top reactions by abs flux
    top_reactions = sorted([(rid, v) for rid, v in fluxes.items() if abs(v) >= min_abs_flux], key=lambda x: abs(x[1]), reverse=True)[:top_n]
    edges = []
    for rid, v in top_reactions:
        try:
            rxn = model.reactions.get_by_id(rid)
        except Exception:
            continue
        reactants = [m for m, coeff in rxn.metabolites.items() if coeff < 0]
        products = [m for m, coeff in rxn.metabolites.items() if coeff > 0]
        if not reactants or not products:
            continue
        denom = max(len(reactants) * len(products), 1)
        share = abs(v) / denom
        for r in reactants:
            for p in products:
                edges.append({
                    'source': r.id,
                    'target': p.id,
                    'flux': share,
                    'reaction': rid,
                    'direction': 'forward' if v >= 0 else 'reverse'
                })
    return edges


def escher_html(map_json: bytes, model, fluxes: Dict[str, float]) -> Optional[str]:
    """Render Escher map HTML with reaction_data overlay if escher is available.

    Returns HTML string or None if escher is not installed/available.
    """
    try:
        from escher import Builder
    except Exception:
        return None

    try:
        builder = Builder(map_json=map_json.decode('utf-8'), model=model, reaction_data=fluxes)
        return builder._repr_html_()
    except Exception:
        return None


def plotly_sankey(edges: List[Dict]) -> Optional["Figure"]:
    """Build a Plotly Sankey Figure from edges. Returns None if plotly not available."""
    try:
        import plotly.graph_objects as go
    except Exception:
        return None

    if not edges:
        return None

    # Map node ids to indices
    nodes = {}
    def idx(node):
        if node not in nodes:
            nodes[node] = len(nodes)
        return nodes[node]

    sources = []
    targets = []
    values = []
    labels = []
    for e in edges:
        s = idx(e['source'])
        t = idx(e['target'])
        sources.append(s)
        targets.append(t)
        values.append(max(e.get('flux', 0.0), 0.0))
    labels = list(nodes.keys())

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=10, thickness=12, line=dict(color="black", width=0.3), label=labels),
        link=dict(source=sources, target=targets, value=values)
    )])
    fig.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10))
    return fig
