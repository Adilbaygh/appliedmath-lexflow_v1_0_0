# AppliedMath LexFlow

Reproducible deterministic lexicographic flow allocation on lossy, capacitated rooted trees. This repository contains the mathematical model, exact benchmark instances, Python implementation, automated verification, and publication assets for a stand-alone *AppliedMath* research article.

## Scientific scope

The project studies deterministic rooted-tree allocation with fixed demands, capacities, efficiencies, routes, and positive service weights. It does not use scenario optimization, stochastic programming, robust optimization, probability distributions, uncertainty sets, chance constraints, or recourse decisions.

The study covers:

1. a loss-aware graph operator mapping net demand to gross edge and source loads;
2. a closed-form Stage-1 max–min fairness optimum;
3. equivalence between the path operator and an independent node-balance system;
4. a deterministic three-stage lexicographic selection rule;
5. exact rational verification and reproducible publication assets.

The five small synthetic benchmarks are designed to isolate mathematical
properties. The Gone Abat Jap instance is a deterministic controlled-scenario
adaptation of openly cited input data. Neither component constitutes field
calibration, historical scarcity validation, or a claim about operational
performance in a particular irrigation system.

## Installation

```powershell
python -m venv my-env
my-env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Unified entry point

Launch the desktop GUI:

```powershell
python main.py
```

Run the terminal benchmark demo:

```powershell
python main.py demo --benchmark temporal_lexicographic
```

Regenerate all article tables and figures:

```powershell
python main.py analysis
```

Installed console commands:

```powershell
appliedmath-lexflow
appliedmath-lexflow-gui
appliedmath-lexflow-demo --benchmark temporal_lexicographic
appliedmath-lexflow-analysis
```

## Desktop GUI

The bilingual Uzbek/English Tk/ttk desktop application uses the same solver and
verification functions as the command-line and reporting pipelines. Select
**Language / Тил** or press `Ctrl+L` to switch languages without changing the
solver snapshot. It provides benchmark selection, Stage 1/2/3 metrics,
allocation tables and temporal profiles, network topology, verification gates,
CSV/Excel export, automated tests, article-output generation, and a browser for
generated result files.

## Repository layout

```text
Model/                       mathematical specification, theorems, and proofs
paper/                       private working manuscript files (excluded from public data package)
Data/benchmarks/             deterministic rooted-tree benchmark instances
src/                         Python package and desktop application
results/tables/               cross-benchmark comparison tables for the Results section
results/figures/              600 dpi PNG for theory-only figures (not tied to one benchmark)
results/figure_data/          source data for the theory-only figures
results/<benchmark_name>/     each benchmark's own figures/ (600 dpi PNG) and figure_data/
results/manifests/            software environment and SHA-256 provenance record
tests/                        automated mathematical and implementation checks
```

Every table-bearing folder above (`tables/`, `figure_data/`, and each
benchmark's own `figure_data/`) holds the same tables twice, in matching
subfolders: `csv/` (for downstream/automated processing) and `excel/` (a
directly readable `.xlsx` copy). For example:

```text
results/tables/csv/table_1_closed_form_verification.csv
results/tables/excel/table_1_closed_form_verification.xlsx
```

## Reproducibility gates

A run is accepted only when:

- the Stage-1 closed form and HiGHS LP agree within `5e-7`;
- the exact path operator and exact node balance agree with zero rational residual;
- all physical constraints are satisfied;
- Stage 3 preserves the Stage-1 floor and Stage-2 objective within tolerance;
- Stage 3 does not increase consecutive-period variation.

Run the tests:

```powershell
python -m pytest -p no:cacheprovider
```

The current release passes 22 automated tests. Across six deterministic
benchmarks, the maximum closed-form/LP difference is approximately `1.11e-16`;
exact operator–balance and node-balance residuals are zero. All five generated
scale instances (up to 500 users, 1022 edges, four periods, and 2000 active
records) have the exact Stage-1 value `0.60`, and the sparse HiGHS LP agrees to
floating-point precision. In the temporal benchmark, the Stage-2 optimal face
has variation range `[0.40, 1.05]`; Stage 3 returns the invariant minimum
`0.40`. The current HiGHS vertex has variation `0.75`, so its observed reduction
is `46.7%`; the `61.9%` value is only the worst-to-best range reduction, not a
guarantee from every Stage-2 optimum.

## Public software release

The public repository should contain the code, model documentation, benchmark
data, tests, source tables, and reproducibility metadata. The private Uzbek
manuscript and licensed journal template remain outside the curated Mendeley
package. Before publication, add the real tagged repository URL to
`CITATION.cff`, decide whether the new archive is Version 2 of the existing Gone
Abat Jap dataset or a distinct related dataset, and cite the assigned DOI in the
Data and Code Availability Statement. The local upload metadata and package
builder are under `mendeley/` and `scripts/build_mendeley_package.py`.
