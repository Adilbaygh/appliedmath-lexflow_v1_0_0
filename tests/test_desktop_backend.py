from pathlib import Path

from appliedmath_lexflow.desktop_backend import (
    benchmark_description,
    benchmark_names,
    ratio_rows,
    resource_label,
    solve_benchmark,
    stage_rows,
    verification_rows,
)
from appliedmath_lexflow.i18n import SUPPORTED_LANGUAGES, tr

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_desktop_backend_uses_shared_solver() -> None:
    names = benchmark_names(PROJECT_ROOT)
    assert "temporal_lexicographic" in names

    snapshot = solve_benchmark(PROJECT_ROOT, "temporal_lexicographic")
    assert snapshot.verification_passed
    assert snapshot.solution.stage3.minimum_ratio >= float(snapshot.closed_form.lambda_star) - 5e-7
    assert snapshot.solution.stage3.temporal_variation <= snapshot.solution.stage2.temporal_variation + 5e-7
    assert len(ratio_rows(snapshot)) == len(snapshot.model.active_records)
    assert all(row[3] == "PASS" for row in verification_rows(snapshot))


def test_uzbek_and_english_presentations_use_the_same_snapshot() -> None:
    snapshot = solve_benchmark(PROJECT_ROOT, "temporal_lexicographic")

    uz_stages = stage_rows(snapshot, "uz")
    en_stages = stage_rows(snapshot, "en")
    assert tuple(row[1:4] for row in uz_stages) == tuple(row[1:4] for row in en_stages)
    assert uz_stages[0][0] == "1-босқич"
    assert en_stages[0][0] == "Stage 1"

    uz_checks = verification_rows(snapshot, language="uz")
    en_checks = verification_rows(snapshot, language="en")
    assert tuple((row[1], row[3]) for row in uz_checks) == tuple(
        (row[1], row[3]) for row in en_checks
    )
    assert uz_checks[0][0] == "Ёпиқ ечим — LP мослиги"
    assert en_checks[0][0] == "Closed form — LP agreement"
    assert all(row[3] == "PASS" for row in en_checks)
    assert float(en_checks[5][1]) <= 5e-7
    assert en_checks[5][2] == "≤ 5.0e-07"

    assert "вақтли мисол" in benchmark_description(snapshot.model, "uz")
    assert "three-period" in benchmark_description(snapshot.model, "en")
    assert resource_label("source:k1", "uz") == "манба:k1"
    assert resource_label("source:k1", "en") == "source:k1"


def test_gui_translation_catalog_supports_both_languages() -> None:
    assert SUPPORTED_LANGUAGES == ("uz", "en")
    assert tr("ready", "uz") == "Тайёр"
    assert tr("ready", "en") == "Ready"
    assert "v0.4.0" in tr("footer", "en")
