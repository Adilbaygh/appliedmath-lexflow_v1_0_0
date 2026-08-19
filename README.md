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

The small synthetic benchmarks are designed to isolate mathematical properties. They do not constitute field calibration, historical validation, or a claim about operational performance in a particular irrigation system.

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

The Tk/ttk desktop application uses the same solver and verification functions as the command-line and reporting pipelines. It provides benchmark selection, Stage 1/2/3 metrics, allocation tables and temporal profiles, network topology, verification gates, CSV export, automated tests, article-output generation, and a browser for generated result files.

## Repository layout

```text
Model/                       mathematical specification, theorems, and proofs
Paper/                       AppliedMath template, manuscript, bibliography, and supplement
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

The current release passes seven automated tests. Across five deterministic benchmarks, the maximum closed-form/LP difference is approximately `1.11e-16`; exact operator–balance and node-balance residuals are zero. In the temporal benchmark, Stage 3 reduces total ratio variation from `0.75` to approximately `0.40` while preserving the Stage-1 minimum ratio `0.60` and Stage-2 weighted satisfaction within numerical tolerance.

## Public software release

The public repository should contain the code, model documentation, benchmark data, tests, source tables, and reproducibility metadata. The private Uzbek manuscript and licensed journal template should remain outside the public software release. Before publication, update `CITATION.cff`, create a tagged release, archive it with a persistent DOI, and cite that release in the Data and Code Availability Statement.
