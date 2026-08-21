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

## Public repository layout

```text
Model/                       mathematical specification, theorems, and proofs
Data/benchmarks/             deterministic rooted-tree benchmark instances
Data/synthetic_*.json        deterministic scale-verification instance
src/                         Python package and desktop application
tests/                        automated mathematical and implementation checks
results/tables/csv/           version-controlled source tables for the Results section
results/manifests/            version-controlled environment and SHA-256 provenance record
.github/workflows/            deterministic continuous-integration checks
```

The public Git tree deliberately keeps the compact CSV source tables and
provenance metadata. Run `python main.py analysis` to regenerate the complete
local publication-output tree: 600 dpi PNG figures, figure-source CSV files,
Excel mirrors, and benchmark-specific result folders. For example, the command
preserves the tracked CSV file and creates its Excel mirror locally:

```text
results/tables/csv/table_1_closed_form_verification.csv
results/tables/excel/table_1_closed_form_verification.xlsx
```

The private manuscript, licensed journal template, local review files, and
Mendeley upload workspace are intentionally excluded from the public software
repository.

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

The public repository contains the code, model documentation, benchmark data,
tests, compact source tables, and reproducibility metadata. Version `0.4.0` is
identified by the tagged GitHub release
[`v0.4.0`](https://github.com/Adilbaygh/appliedmath-lexflow_v1_0_0/releases/tag/v0.4.0).
The private Uzbek manuscript, licensed journal template, local review files,
and Mendeley upload workspace remain outside this public repository and outside
the curated public software archive. When Mendeley assigns the archive DOI, add
that DOI to the archive metadata and to the article's Data and Code Availability
Statement; no provisional DOI is recorded here.
