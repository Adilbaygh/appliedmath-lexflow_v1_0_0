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

To reproduce the audited dependency set recorded in the run manifest, replace
the last command with:

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
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
Data/README.md               provenance of every instance: which parameters are
                             published, which are imposed, and by which rule
Data/benchmarks/             deterministic rooted-tree benchmark instances
Data/design/                 counterexample instance and the scripts that re-derive
                             every author-imposed parameter
Data/synthetic_*.json        deterministic scale-verification instance
src/                         Python package and desktop application
tests/                        automated mathematical and implementation checks
results/tables/csv/           version-controlled source tables for the Results section
results/manifests/            version-controlled environment and SHA-256 provenance record
results/timing/               machine-dependent timing measurements (bench scripts)
results/perturbation/         perturbation study of the controlled scenario (bench script)
bench/                        command-line scripts for the additional analyses
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
- Stage 3 does not increase consecutive-period variation;
- on all 400 randomized instances (seven families with prescribed capacity
  ratios and three with capacities drawn independently of the loads) the same
  thresholds hold, and the bottleneck named by the closed form is confirmed by
  the Stage-1 LP alone (sufficiency and necessity tests).

Run the tests:

```powershell
python -m pytest -p no:cacheprovider
```

The current release passes 76 automated tests. Across six deterministic
benchmarks, the maximum closed-form/LP difference is approximately `1.11e-16`;
exact operator–balance and node-balance residuals are zero. All five generated
scale instances (up to 500 users, 1022 edges, four periods, and 2000 active
records) have the exact Stage-1 value `0.60`, and the sparse HiGHS LP agrees to
floating-point precision. In the temporal benchmark, the Stage-2 optimal face
has variation range `[0.40, 1.05]`; Stage 3 returns the invariant minimum
`0.40`. The current HiGHS vertex has variation `0.75`, so its observed reduction
is `46.7%`; the `61.9%` value is only the worst-to-best range reduction, not a
guarantee from every Stage-2 optimum.

## Additional analyses

These analyses answer the third review round. The deterministic ones are part
of `python run_analysis.py`; the three machine-dependent or long-running ones
are separate scripts whose outputs `run_analysis.py` preserves and records in
the manifest.

| Analysis | Command | Output |
|---|---|---|
| Randomized robustness suite, bottleneck identification, Stage-3 activity | `run_analysis.py` (console view: `python bench/robustness_suite.py`) | `results/tables/csv/table_A3_robustness_*.csv` |
| Comparison with alternative allocation rules | `run_analysis.py` | `results/tables/csv/table_9_rule_comparison*.csv` |
| Alternative Stage-3 smoothness criteria and block-specific variation limits | `run_analysis.py` | `results/tables/csv/table_10_*.csv` |
| Service-weight sweep, five weighting rules and their winners and losers (synthetic weights) | `run_analysis.py` (console view: `python bench/weight_sweep.py`) | `results/tables/csv/table_A4_*.csv`, `table_A5_*.csv` |
| Parameter perturbation of the controlled scenario | `python bench/perturbation.py` | `results/perturbation/` |
| Stage-1 closed form versus LP, phase-resolved timing | `python bench/scale_timing.py` | `results/timing/scale_timing*.csv`, `environment.json` |
| Wall-clock time of every allocation rule | `python bench/compare_rules.py` | `results/timing/rule_comparison_timing.csv` |

The perturbation study re-solves the deterministic model for perturbed inputs;
it is a sensitivity analysis of the results, not a stochastic or robust
formulation.

## Where each table and figure of the manuscript comes from

The file names follow the package's own numbering, which predates the final
table numbers of the manuscript. Every file below is regenerated by
`python run_analysis.py`, except the three machine-dependent outputs marked
with an asterisk, which come from the scripts listed in the previous section.

| Manuscript | Source file(s) |
|---|---|
| Table 1 | `results/tables/csv/table_1_closed_form_verification.csv` |
| Table 2 | `results/tables/csv/table_2_operator_balance_verification.csv` |
| Table 3 | `results/tables/csv/table_3_lexicographic_stages.csv` |
| Table 4 | `results/tables/csv/table_5_invariant_variation_and_price_of_fairness.csv` |
| Table 5 | `results/tables/csv/table_6_leximin_allocation.csv` |
| Table 6 | `results/tables/csv/table_7_scale_verification.csv`; times and memory `results/timing/scale_timing.csv`* |
| Table 7 | `results/tables/csv/table_8_weight_sensitivity.csv` |
| Table 8 | `results/tables/csv/table_A3_robustness_suite.csv` (per instance: `table_A3_robustness_instances.csv`) |
| Table 9 | `results/tables/csv/table_9_rule_comparison_random_summary.csv`; times `results/timing/rule_comparison_timing.csv`* |
| Table 10 | `results/perturbation/csv/perturbation_summary.csv`* (per draw: `perturbation_draws.csv`) |
| Table A1 | qualitative comparison, no data file |
| Table A2 | `results/tables/csv/table_A2_controlled_scenario_periods.csv` (reach ratios of Appendix A.4: `table_A2_controlled_scenario_reach_ratios.csv`) |
| Table A3 | `results/tables/csv/table_A3_robustness_suite.csv` |
| Table A4 | `results/tables/csv/table_A4_weight_ratio_sweep.csv` |
| Table A5 | `results/tables/csv/table_A5_weighting_rules.csv`, `table_A5_weighting_rules_summary.csv` |
| Table A6 | `results/tables/csv/table_10_smoothness_criteria.csv`; Section 5.2: `table_10_smoothness_criteria_random_summary.csv`, `table_10_block_variation_limits.csv` |
| Figures 1, 5, 6, 7 | `results/branching_shared_edge_bottleneck/figures/` (Figure 1, 6, 7) and `results/temporal_lexicographic/figures/figure_5_profiles.png` |
| Figures 2, 3, 4 | `results/figures/` |
| Figures 8, 9 | `results/gone_abat_jap/figures/figure_1_tree.png`, `figure_5_profiles.png` |

## Public software release

The public repository contains the code, model documentation, benchmark data,
tests, compact source tables, and reproducibility metadata. Version `0.5.2` is
identified by the tagged GitHub release
[`v0.5.2`](https://github.com/Adilbaygh/appliedmath-lexflow_v1_0_0/releases/tag/v0.5.2).
The private Uzbek manuscript, licensed journal template and local review files
remain outside this public repository and outside the curated public software
archive. Each tagged release is archived on Zenodo under the concept DOI
[10.5281/zenodo.22669687](https://doi.org/10.5281/zenodo.22669687), which
resolves to the latest archived version; the version DOI of that release is the
one cited in the article's Data Availability Statement.
