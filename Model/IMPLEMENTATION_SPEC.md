# Deterministic implementation specification

## Non-negotiable boundary

- Input instances are declared, deterministic rooted trees. The analytical
  suite is small; the separate scale suite reaches 500 users and 1022 edges.
- The Gone Abat Jap topology is a transparent controlled-scenario adaptation
  of an openly cited dataset, not an observed scarcity record or field
  validation result.
- No scenario, uncertainty, probability, robust counterpart, or recourse module is permitted.
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
8. Stage-3 minimum ratio preserves $\lambda^*$;
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

## Publication outputs

Each execution writes:

- CSV and Excel tables;
- separate CSV source data for every figure;
- PNG figures at 600 dpi;
- SHA-256 run manifest;
- JSON result summaries.

The manuscript may use only outputs produced by a run that passes all automated tests.

For a degenerate Stage-2 face, a solver-returned $\Omega(r^{(2)})$ is reported
only as a selected vertex diagnostic. The invariant results are
$\Omega_{\min}$ and $\Omega_{\max}$. The quotient
$(\Omega_{\max}-\Omega_{\min})/\Omega_{\max}$ is labelled a worst-to-best range
reduction, never a guaranteed reduction from an arbitrary Stage-2 optimum.
