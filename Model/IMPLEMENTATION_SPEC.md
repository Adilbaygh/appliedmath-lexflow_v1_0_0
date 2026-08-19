# Deterministic implementation specification

## Non-negotiable boundary

- Input instances are small, declared, deterministic rooted trees.
- No real-network dataset is imported.
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

## Publication outputs

Each execution writes:

- CSV tables;
- separate CSV source data for every figure;
- PNG figures at 600 dpi;
- PDF and SVG figure copies;
- SHA-256 run manifest;
- a short JSON result summary.

The manuscript may use only outputs produced by a run that passes all automated tests.
