# Deterministic implementation specification

## Non-negotiable boundary

- Input instances are declared, deterministic rooted trees. The analytical
  suite is small; the separate scale suite reaches 500 users and 1022 edges.
- The Gone Abat Jap topology is a transparent controlled-scenario adaptation
  of an openly cited dataset, not an observed scarcity record or field
  validation result.
- No scenario, uncertainty, probability, robust counterpart, or recourse module is permitted
  inside the model. The perturbation study (`perturbation.py`) is a sensitivity
  analysis of the results: it re-solves the same deterministic model for
  perturbed inputs and adds no random variable to the formulation.
- All benchmark numbers are stored as rational strings in JSON.

## Exact layer

The package uses `fractions.Fraction` for:

- demands, capacities, and efficiencies;
- graph-operator coefficients;
- Stage-1 closed form;
- path-operator flows;
- recursive node-balance flows;
- exact residual comparison.

## Numerical layer

SciPy HiGHS solves the three LP stages. The numerical layer must be checked against exact analytical oracles whenever an exact oracle exists.

## Mandatory gates

1. JSON schema/domain validation;
2. rooted-tree connectivity and unique incoming edge for every non-source node;
3. $0<\eta\le1$ and nonnegative demand/capacity;
4. exact operator-node balance difference equals zero;
5. exact node residual equals zero;
6. $|\lambda^{\mathrm{LP}}-\lambda^{\mathrm{cf}}|\le5\times10^{-7}$;
7. no positive physical-constraint violation above $5\times10^{-7}$;
8. Stage-3 minimum ratio preserves $\lambda^{\ast}$;
9. Stage-3 weighted satisfaction preserves the Stage-2 optimum within declared floating tolerance;
10. Stage-3 temporal variation does not exceed Stage-2 variation.
11. the Stage-2 objective is preserved in both directions within the declared
    tolerance (an absolute equality residual, not a one-sided check);
12. price of fairness uses the same positive weight vector in the efficiency
    and fairness-constrained problems;
13. the generated five-instance scale suite matches the exact value $3/5$ and
    the sparse HiGHS Stage-1 LP within $5\times10^{-7}$.
14. Uzbek and English GUI presentation layers return identical numerical
    values from the same immutable solver snapshot.
15. on every instance of the randomized suite (`robustness.py`, 400 instances,
    seeds 20260916 and 20260921) the acceptance gates G1 and G3–G8 of the
    manuscript hold with the thresholds of its Section 2.9, unchanged; the
    relative physical residual G5r does not exceed $10^{-9}$;
16. on every randomized instance with $\lambda^{\ast}<1$ each resource named by
    the closed form is tight at the Stage-1 LP and Stage-3 optima, relaxing all
    other resources tenfold leaves the Stage-1 LP value unchanged, and relaxing
    the near-minimizer set by 0.1% raises it;
17. Stage 3 lowers $\Omega$ only on instances whose Stage-2 optimal face is not
    a single point;
18. in the rule comparison (`comparison.py`) the three-stage, equal-proportional
    and leximin allocations keep the guarantee $\lambda^{\ast}$ on every
    benchmark and every randomized instance with independent capacities.

## Publication outputs

Each execution writes:

- CSV and Excel tables;
- separate CSV source data for every figure;
- PNG figures at 600 dpi;
- SHA-256 run manifest;
- JSON result summaries;
- the additional analyses of the third review round: `table_A3_robustness_*`,
  `table_9_rule_comparison*`, `table_10_smoothness_criteria*`,
  `table_A4_weight_ratio_sweep` and `table_A5_weighting_rules`.

Two further folders are written by separate scripts and are preserved and
hashed by every analysis run: `results/timing/` (`bench/scale_timing.py`,
`bench/compare_rules.py`; wall-clock times, median/IQR/minimum, environment
record) and `results/perturbation/` (`bench/perturbation.py`).

The manuscript may use only outputs produced by a run that passes all automated tests.

For a degenerate Stage-2 face, a solver-returned $\Omega(r^{(2)})$ is reported
only as a selected vertex diagnostic. The invariant results are
$\Omega_{\min}$ and $\Omega_{\max}$. The quotient
$(\Omega_{\max}-\Omega_{\min})/\Omega_{\max}$ is labelled a worst-to-best range
reduction, never a guaranteed reduction from an arbitrary Stage-2 optimum.
