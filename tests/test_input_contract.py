from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from appliedmath_lexflow.io import load_benchmark, validate_benchmark

DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def test_model_requires_at_least_one_active_service_record() -> None:
    model = load_benchmark(DATA / "chain_source_bottleneck.json")
    empty_demand = {
        period: {user: Fraction(0) for user in model.user_ids}
        for period in model.periods
    }
    with pytest.raises(ValueError, match="positive-demand"):
        validate_benchmark(replace(model, demand=empty_demand))


def test_users_must_be_assigned_to_terminal_leaves() -> None:
    model = load_benchmark(DATA / "chain_source_bottleneck.json")
    invalid_users = (replace(model.users[0], terminal=model.source),)
    with pytest.raises(ValueError, match="terminal leaf"):
        validate_benchmark(replace(model, users=invalid_users))
