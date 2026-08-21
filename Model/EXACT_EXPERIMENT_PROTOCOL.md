# Exact deterministic experiment protocol

## Evidence question

Do the analytical formulae and equivalent formulations of the deterministic lexicographic tree-flow model agree exactly on independently constructed rooted-tree benchmark instances, and does the third lexicographic stage provide a strictly smoother selector when Stage 2 is degenerate?

## Benchmark family

1. `chain_source_bottleneck`: source-limited chain;
2. `star_edge_bottleneck`: unique local-edge bottleneck;
3. `branching_shared_edge_bottleneck`: shared internal-edge bottleneck;
4. `tie_bottleneck`: simultaneous source and edge bottlenecks;
5. `temporal_lexicographic`: multiple Stage-2 optima and strict Stage-3 smoothing.

## E1. Closed-form verification

For each benchmark compute $\lambda^{\mathrm{cf}}$ exactly and solve Stage 1 with HiGHS. Require

$$
|\lambda^{\mathrm{LP}}-\lambda^{\mathrm{cf}}|\le5\times10^{-7}.
$$

## E2. Operator-balance equivalence

Set the canonical Stage-1 vector $r_{kf}=\lambda^{\ast}$. Compute gross flows by:

1. path-product graph operator;
2. reverse-topological node-balance recursion.

Require exact rational equality for every edge-period pair and exact zero node residual.

## E3. Lexicographic preservation

For all instances, solve all three stages and verify:

$$
\min r^{(2)}\ge\lambda^{\ast},
\qquad
\min r^{(3)}\ge\lambda^{\ast},
$$

$$
\left|S(r^{(3)})-S(r^{(2)})\right|\le\tau,
$$

$$
\Omega(r^{(3)})\le\Omega(r^{(2)})+\tau.
$$

## E4. Strict smoothing challenge

For `temporal_lexicographic`, require

$$
\Omega(r^{(3)})<\Omega(r^{(2)}).
$$

The current HiGHS version selects a Stage-2 vertex with $\Omega=0.75$, while
Stage 3 returns $\Omega_{\min}=2/5=0.40$. Because the Stage-2 optimal-face range
is $[2/5,21/20]$, the value $0.75$ is a solver-vertex diagnostic rather than an
invariant property.

## E5. Deterministic scale suite

Generate complete binary trees for $F\in\{20,50,100,250,500\}$ with
$P=2^{\lceil\log_2F\rceil}$ leaves. Require the exact node-balance evaluation
and a path-sparse HiGHS Stage-1 LP to return $\lambda^{\ast}=3/5$ within
$5\times10^{-7}$ for every size.

## E6. Reproducibility

Record dependency versions, platform information, input SHA-256 hashes, output SHA-256 hashes, and UTC generation time. Rerunning the same commit and dependency set must reproduce all exact tables and preserve numerical values within the declared tolerance.
