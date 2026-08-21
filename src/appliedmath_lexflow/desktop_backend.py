"""Pure backend services used by the AppliedMath desktop application.

The functions in this module do not create GUI objects.  They are therefore easy
to test in headless CI environments and guarantee that the desktop application,
 command-line demo, and article-output pipeline use the same mathematical code.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from fractions import Fraction
from pathlib import Path

import pandas as pd

from .domain import Benchmark
from .examples import load_all_benchmarks
from .lexicographic import ThreeStageSolution, solve_three_stage
from .operators import build_operator_exact
from .stage1 import (
    Stage1ClosedForm,
    Stage1LP,
    solve_stage1_closed_form,
    solve_stage1_lp,
)
from .tables import write_table
from .verification import (
    OperatorVerification,
    maximum_physical_violation,
    verify_operator_exact,
)

_BENCHMARK_DESCRIPTIONS = {
    "uz": {
    "branching_shared_edge_bottleneck": (
        "Иккита қуйи истеъмолчи учун умумий ички қирра чекловчи ресурс бўладиган "
        "тармоқланувчи дарахт мисоли."
    ),
    "chain_source_bottleneck": (
        "Бир истеъмолчили кетма-кет канал занжири; биринчи босқич оптимумини манба "
        "ҳажми белгилайди."
    ),
    "star_edge_bottleneck": (
        "Икки терминалли юлдузсимон тармоқ; битта маҳаллий қирра ягона чекловчи "
        "ресурс ҳисобланади."
    ),
    "temporal_lexicographic": (
        "Уч давр ва икки истеъмолчидан иборат вақтли мисол; иккинчи босқичда бир нечта "
        "тенг оптимал ечим мавжуд, учинчи босқич эса улар орасидан вақт бўйича "
        "силлиқроқ тақсимотни танлайди."
    ),
    "tie_bottleneck": (
        "Манба ва маҳаллий қирра бир вақтда $\\lambda=3/4$ қийматида чекловчи "
        "ресурс бўладиган юлдузсимон тармоқ."
    ),
    },
    "en": {
        "branching_shared_edge_bottleneck": (
            "A branching tree in which one shared internal edge is the binding "
            "resource for two downstream users."
        ),
        "chain_source_bottleneck": (
            "A single-user serial canal chain whose Stage-1 optimum is determined "
            "by source capacity."
        ),
        "star_edge_bottleneck": (
            "A two-terminal star network in which one local edge is the unique "
            "binding resource."
        ),
        "temporal_lexicographic": (
            "A three-period, two-user example with multiple Stage-2 optima; Stage 3 "
            "selects a temporally smoother allocation from that optimal face."
        ),
        "tie_bottleneck": (
            "A star network in which the source and a local edge bind simultaneously "
            "at lambda = 3/4."
        ),
    },
}


def benchmark_description(model: Benchmark, language: str = "uz") -> str:
    """Return a localized description while preserving the source benchmark."""

    from .i18n import normalize_language

    language = normalize_language(language)
    return _BENCHMARK_DESCRIPTIONS[language].get(model.name, model.description)


def benchmark_description_uz(model: Benchmark) -> str:
    """Backward-compatible Uzbek description helper."""

    return benchmark_description(model, "uz")


def resource_label(label: str, language: str = "uz") -> str:
    from .i18n import normalize_language

    language = normalize_language(language)
    if label == "demand_upper_bound":
        return "талабнинг юқори чегараси" if language == "uz" else "demand upper bound"
    if label.startswith("source:"):
        prefix = "манба:" if language == "uz" else "source:"
        return prefix + label.removeprefix("source:")
    if label.startswith("edge:"):
        prefix = "қирра:" if language == "uz" else "edge:"
        return prefix + label.removeprefix("edge:")
    return label


def resource_label_uz(label: str) -> str:
    """Backward-compatible Uzbek resource helper."""

    return resource_label(label, "uz")


@dataclass(frozen=True, slots=True)
class BenchmarkSnapshot:
    """Complete deterministic solution and verification record for one benchmark."""

    model: Benchmark
    closed_form: Stage1ClosedForm
    stage1_lp: Stage1LP
    operator_verification: OperatorVerification
    solution: ThreeStageSolution
    maximum_physical_violation: float

    @property
    def closed_form_lp_difference(self) -> float:
        return abs(self.stage1_lp.lambda_star - float(self.closed_form.lambda_star))

    @property
    def verification_passed(self) -> bool:
        return all(row[3] == "PASS" for row in verification_rows(self))


@dataclass(frozen=True, slots=True)
class ResultFile:
    relative_path: str
    size_bytes: int
    modified_at: str


def fraction_string(value: Fraction) -> str:
    """Return an exact rational value without losing precision."""

    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def find_project_root(start: str | Path | None = None) -> Path:
    """Locate the repository root from a launcher, package, or current directory."""

    if start is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start).expanduser().resolve()

    if start_path.is_file():
        start_path = start_path.parent

    candidates = (start_path, *start_path.parents)
    for candidate in candidates:
        if (candidate / "Data" / "benchmarks").is_dir() and (candidate / "pyproject.toml").is_file():
            return candidate

    package_root = Path(__file__).resolve().parents[2]
    for candidate in (package_root, *package_root.parents):
        if (candidate / "Data" / "benchmarks").is_dir() and (candidate / "pyproject.toml").is_file():
            return candidate

    raise FileNotFoundError(
        "AppliedMath project root was not found. Open the repository root in VS Code "
        "or start the application from the folder containing pyproject.toml."
    )


def load_benchmarks(project_root: str | Path) -> dict[str, Benchmark]:
    root = find_project_root(project_root)
    models = load_all_benchmarks(root / "Data" / "benchmarks")
    if not models:
        raise FileNotFoundError(f"No benchmark JSON files were found in {root / 'Data' / 'benchmarks'}")
    return {model.name: model for model in models}


def benchmark_names(project_root: str | Path) -> tuple[str, ...]:
    return tuple(sorted(load_benchmarks(project_root)))


def _solve_snapshot(model: Benchmark) -> BenchmarkSnapshot:
    closed = solve_stage1_closed_form(model)
    stage1_lp = solve_stage1_lp(model)
    canonical_ratios = {record: closed.lambda_star for record in model.active_records}
    operator_verification = verify_operator_exact(model, canonical_ratios)
    solution = solve_three_stage(model)
    a_coeff, b_coeff = build_operator_exact(model)
    physical_violation = maximum_physical_violation(
        model, solution.stage3.ratios, a_coeff, b_coeff
    )
    return BenchmarkSnapshot(
        model=model,
        closed_form=closed,
        stage1_lp=stage1_lp,
        operator_verification=operator_verification,
        solution=solution,
        maximum_physical_violation=physical_violation,
    )


def solve_benchmark(project_root: str | Path, benchmark_name: str) -> BenchmarkSnapshot:
    """Solve all three deterministic stages and run independent checks."""

    models = load_benchmarks(project_root)
    try:
        model = models[benchmark_name]
    except KeyError as exc:
        available = ", ".join(sorted(models))
        raise KeyError(f"Unknown benchmark {benchmark_name!r}. Available: {available}") from exc
    return _solve_snapshot(model)


def solve_benchmark_at_path(path: str | Path) -> BenchmarkSnapshot:
    """Load and solve a single benchmark JSON file at an arbitrary path.

    Used by the desktop app's file-open dialog, which lets the user pick any
    benchmark file directly instead of choosing a name from a preloaded list.
    """
    from .io import load_benchmark

    model = load_benchmark(Path(path))
    return _solve_snapshot(model)


def stage_rows(
    snapshot: BenchmarkSnapshot, language: str = "uz"
) -> tuple[tuple[str, str, str, str, str], ...]:
    """Return presentation-ready Stage 1/2/3 rows."""

    from .i18n import normalize_language

    language = normalize_language(language)
    stage_names = {
        "uz": {"Stage 1": "1-босқич", "Stage 2": "2-босқич", "Stage 3": "3-босқич"},
        "en": {"Stage 1": "Stage 1", "Stage 2": "Stage 2", "Stage 3": "Stage 3"},
    }
    optimal = "ОПТИМАЛ" if language == "uz" else "OPTIMAL"
    rows: list[tuple[str, str, str, str, str]] = []
    for stage in (snapshot.solution.stage1, snapshot.solution.stage2, snapshot.solution.stage3):
        rows.append(
            (
                stage_names[language].get(stage.name, stage.name),
                f"{stage.minimum_ratio:.9f}",
                f"{stage.weighted_satisfaction:.9f}",
                f"{stage.temporal_variation:.9f}",
                optimal if stage.status == 0 else str(stage.status),
            )
        )
    return tuple(rows)


def ratio_rows(snapshot: BenchmarkSnapshot) -> tuple[tuple[str, str, str, str, str, str], ...]:
    """Return one row per active period-user record."""

    model = snapshot.model
    result: list[tuple[str, str, str, str, str, str]] = []
    for period, user in model.active_records:
        result.append(
            (
                period,
                user,
                fraction_string(model.demand[period][user]),
                f"{snapshot.solution.stage1.ratios[(period, user)]:.9f}",
                f"{snapshot.solution.stage2.ratios[(period, user)]:.9f}",
                f"{snapshot.solution.stage3.ratios[(period, user)]:.9f}",
            )
        )
    return tuple(result)


def verification_rows(
    snapshot: BenchmarkSnapshot,
    tolerance: float = 5e-7,
    language: str = "uz",
) -> tuple[tuple[str, str, str, str], ...]:
    """Return declared analytical and numerical verification gates."""

    from .i18n import normalize_language

    language = normalize_language(language)
    names = {
        "uz": (
            "Ёпиқ ечим — LP мослиги",
            "Graph operator — node balance фарқи",
            "Тугун баланси қолдиғи",
            "3-босқич физик чеклов бузилиши",
            "3-босқич адолат кафолати",
            "3-босқич қониқишни сақлаши",
            "3-босқич вариацияни оширмаслиги",
        ),
        "en": (
            "Closed form — LP agreement",
            "Graph operator — node balance difference",
            "Node-balance residual",
            "Stage-3 physical-constraint violation",
            "Stage-3 fairness guarantee",
            "Stage-3 satisfaction preservation",
            "Stage-3 non-increase in variation",
        ),
    }[language]
    exact_criterion = "= 0 (аниқ арифметика)" if language == "uz" else "= 0 (exact arithmetic)"
    solution = snapshot.solution
    lambda_star = float(snapshot.closed_form.lambda_star)
    checks: list[tuple[str, str, str, bool]] = [
        (
            names[0],
            f"{snapshot.closed_form_lp_difference:.3e}",
            f"≤ {tolerance:.1e}",
            snapshot.closed_form_lp_difference <= tolerance,
        ),
        (
            names[1],
            fraction_string(snapshot.operator_verification.maximum_absolute_difference),
            exact_criterion,
            snapshot.operator_verification.maximum_absolute_difference == 0,
        ),
        (
            names[2],
            fraction_string(snapshot.operator_verification.maximum_node_residual),
            exact_criterion,
            snapshot.operator_verification.maximum_node_residual == 0,
        ),
        (
            names[3],
            f"{snapshot.maximum_physical_violation:.3e}",
            f"≤ {tolerance:.1e}",
            snapshot.maximum_physical_violation <= tolerance,
        ),
        (
            names[4],
            f"{solution.stage3.minimum_ratio:.9f}",
            f"≥ λ* = {lambda_star:.9f}",
            solution.stage3.minimum_ratio + tolerance >= lambda_star,
        ),
        (
            names[5],
            f"{abs(solution.stage3.weighted_satisfaction - solution.stage2.weighted_satisfaction):.3e}",
            f"≤ {tolerance:.1e}",
            abs(
                solution.stage3.weighted_satisfaction
                - solution.stage2.weighted_satisfaction
            )
            <= tolerance,
        ),
        (
            names[6],
            f"{solution.stage3.temporal_variation:.9f}",
            (
                f"≤ {'2-босқич' if language == 'uz' else 'Stage 2'} = "
                f"{solution.stage2.temporal_variation:.9f}"
            ),
            solution.stage3.temporal_variation
            <= solution.stage2.temporal_variation + tolerance,
        ),
    ]
    return tuple((name, value, criterion, "PASS" if passed else "FAIL") for name, value, criterion, passed in checks)


def result_files(project_root: str | Path) -> tuple[ResultFile, ...]:
    root = find_project_root(project_root)
    output_root = root / "results"
    if not output_root.exists():
        return ()
    items: list[ResultFile] = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        stat = path.stat()
        items.append(
            ResultFile(
                relative_path=str(path.relative_to(root)),
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
    return tuple(items)


def export_snapshot(
    snapshot: BenchmarkSnapshot,
    project_root: str | Path,
    language: str = "uz",
) -> tuple[Path, Path]:
    """Export current GUI values without replacing article-wide generated assets.

    Writes both a ``csv/`` copy (for downstream processing) and an ``excel/``
    copy (convenient for people to open directly).
    """

    root = find_project_root(project_root)
    export_dir = root / "results" / "gui_exports"
    safe_name = snapshot.model.name.replace(" ", "_")

    ratios_frame = pd.DataFrame(
        ratio_rows(snapshot),
        columns=["period", "user", "demand", "stage1_ratio", "stage2_ratio", "stage3_ratio"],
    )
    verification_frame = pd.DataFrame(
        verification_rows(snapshot, language=language),
        columns=["check", "value", "criterion", "status"],
    )
    write_table(ratios_frame, export_dir, f"{safe_name}_allocation_ratios")
    write_table(verification_frame, export_dir, f"{safe_name}_verification")

    ratios_path = export_dir / "csv" / f"{safe_name}_allocation_ratios.csv"
    verification_path = export_dir / "csv" / f"{safe_name}_verification.csv"

    return ratios_path, verification_path



def generate_article_results(project_root: str | Path) -> dict[str, object]:
    """Generate all publication assets in an isolated Python process.

    Matplotlib is kept outside the Tk worker thread, which avoids GUI-backend
    conflicts on Windows and leaves the article pipeline identical to CLI use.
    """

    root = find_project_root(project_root)
    completed = subprocess.run(
        [sys.executable, str(root / "main.py"), "analysis"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        output = "\n".join(
            part for part in (completed.stdout, completed.stderr) if part
        ).strip()
        raise RuntimeError(output or "Мақола натижаларини яратишда номаълум хато.")

    summary_path = root / "results" / "RESULTS_SUMMARY.json"
    if not summary_path.is_file():
        raise FileNotFoundError(
            "Pipeline тугади, аммо results/RESULTS_SUMMARY.json топилмади."
        )
    return json.loads(summary_path.read_text(encoding="utf-8"))


def save_benchmark_result(
    project_root: str | Path, benchmark_path: str | Path, output_dir: str | Path
) -> dict[str, object]:
    """Save one benchmark's full figure/table/figure_data package in an isolated process.

    Works for any benchmark file, not only ones under Data/benchmarks/ — this
    backs the desktop app's "Натижани сақлаш" (Save Result) action, which
    saves whichever file the user currently has open. Matplotlib is kept
    outside the Tk worker thread for the same reason as
    :func:`generate_article_results`.
    """

    root = find_project_root(project_root)
    completed = subprocess.run(
        [
            sys.executable,
            str(root / "main.py"),
            "save-result",
            "--benchmark-path",
            str(benchmark_path),
            "--output-dir",
            str(output_dir),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        output = "\n".join(
            part for part in (completed.stdout, completed.stderr) if part
        ).strip()
        raise RuntimeError(output or "Натижани сақлашда номаълум хато.")

    lines = [line for line in completed.stdout.strip().splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("Pipeline тугади, аммо натижа маълумоти қайтарилмади.")
    try:
        return json.loads(lines[-1])
    except ValueError as exc:
        raise RuntimeError(f"Натижа JSON'ини ўқиб бўлмади:\n{completed.stdout}") from exc


def run_tests(project_root: str | Path) -> tuple[int, str]:
    """Run the repository test suite with the selected Python interpreter."""

    root = find_project_root(project_root)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return completed.returncode, output


def users_with_activity(model: Benchmark) -> tuple[str, ...]:
    active_users = {user for _, user in model.active_records}
    return tuple(user for user in model.user_ids if user in active_users)


def period_series(
    snapshot: BenchmarkSnapshot,
    user: str,
) -> tuple[tuple[str, ...], tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    model = snapshot.model
    periods: list[str] = []
    stage1_values: list[float] = []
    stage2_values: list[float] = []
    stage3_values: list[float] = []
    for period in model.periods:
        record = (period, user)
        if record not in snapshot.solution.stage3.ratios:
            continue
        periods.append(period)
        stage1_values.append(snapshot.solution.stage1.ratios[record])
        stage2_values.append(snapshot.solution.stage2.ratios[record])
        stage3_values.append(snapshot.solution.stage3.ratios[record])
    return tuple(periods), tuple(stage1_values), tuple(stage2_values), tuple(stage3_values)
