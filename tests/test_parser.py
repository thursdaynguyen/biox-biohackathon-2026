import os
from parser import parse_sbml_extracellular

MODEL = os.path.join(os.path.dirname(__file__), '..', 'GCA_000182925.2_gapfilled.xml')


def test_parse_returns_list_and_nonempty():
    items = parse_sbml_extracellular(MODEL)
    assert isinstance(items, list)
    assert len(items) > 0
    # check presence of expected keys
    for s in items[:5]:
        assert 'id' in s and 'name' in s and 'compartment' in s
