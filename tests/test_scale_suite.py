from fractions import Fraction
from pathlib import Path

from appliedmath_lexflow.io import load_benchmark
from appliedmath_lexflow.scales import build_scale_benchmark, verify_scale_suite

ROOT = Path(__file__).resolve().parents[1]


def test_scale_generator_matches_checked_in_500_user_instance() -> None:
    generated = build_scale_benchmark(500)
    checked = load_benchmark(ROOT / "Data" / "synthetic_scale_500u_1022e_4p.json")
    assert generated.nodes == checked.nodes
    assert generated.edges == checked.edges
    assert generated.users == checked.users
    assert generated.periods == checked.periods
    assert generated.demand == checked.demand
    assert generated.efficiency == checked.efficiency
    assert generated.source_capacity == checked.source_capacity
    assert generated.edge_capacity == checked.edge_capacity


def test_all_scale_instances_match_closed_form_and_sparse_lp() -> None:
    rows = verify_scale_suite()
    assert tuple(row.users for row in rows) == (20, 50, 100, 250, 500)
    assert all(row.lambda_closed_form == Fraction(3, 5) for row in rows)
    assert all(row.active_resources == ("source:k4",) for row in rows)
    assert max(row.absolute_difference for row in rows) <= 5e-7
    assert rows[-1].edges == 1022
    assert rows[-1].active_records == 2000
    assert rows[-1].principal_inequalities == 6092
