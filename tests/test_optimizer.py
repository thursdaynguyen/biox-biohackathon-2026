from optimizer import objective_mock_multi


def test_objective_multi_penalizes_byproduct():
    species = [
        {'id': 'glc__D_e', 'name': 'glucose'},
        {'id': 'ac_e', 'name': 'acetate'},
    ]
    # with acetate present, penalty should reduce score
    x_good = {'glc__D_e': 10.0, 'ac_e': 0.0}
    x_bad = {'glc__D_e': 10.0, 'ac_e': 10.0}
    score_good = objective_mock_multi(species, x_good)
    score_bad = objective_mock_multi(species, x_bad)
    assert score_good > score_bad
