# Model development log

## v0.5.2

Changes made for the second report of the third reviewer. The formulation,
Theorems 1 and 2 and every published benchmark value are unchanged.

- `robustness.py` replaces the body of `bench/robustness_suite.py`. The seven
  families of 0.5.1 are reproduced instance by instance; three new families
  draw source and reach capacities independently of the loads. Every instance
  is checked against the Section 2.9 thresholds (previously the suite used its
  own), with G3 and G4 reported separately and a relative physical residual
  G5r added. The bottleneck named by the closed form is confirmed by the
  Stage-1 LP alone, and each instance records whether the Stage-2 face is a
  single point and whether Stage 3 lowers the variation;
- `comparison.py`: the three-stage allocation against total-delivery
  maximization, equal proportional allocation, the weighted single objective
  (35) and full leximin;
- `smoothing.py`: Stage 3 with ratio, demand-weighted, delivered-volume and
  largest-jump criteria over the same Stage-2 face, cross-evaluated;
- `perturbation.py` and `bench/perturbation.py`: five perturbation scenarios of
  the controlled Gone Abat Jap scenario, 200 draws each;
- `weights.py`: Tables A4 and A5 are now written by the analysis run; the
  weights of Table A5 are labelled as synthetic;
- `bench/scale_timing.py` times build, load assembly, closed-form scan, LP
  assembly and LP solve separately, 30 repetitions, median/IQR/minimum, and
  writes CSV files and an environment record; `bench/compare_rules.py` times
  every allocation rule;
- `results/timing/` and `results/perturbation/` are preserved by the analysis
  run and recorded in its manifest;
- `weights.py` adds rule (v) (demand-normalized weights) and a deliberately
  one-sided synthetic rule to Table A5, and reports for every rule which blocks
  gain or lose against uniform weights (`table_A5_weighting_rules_by_block`,
  `_summary`); no rule lowers any block below the guarantee;
- `smoothing.block_variation_limits` computes, per block, the smallest
  period-to-period variation limit the Stage-2 face admits, whether those limits
  are jointly attainable, and a demand-scaled limit rule
  (`table_10_block_variation_limits`);
- the Theorem 1 proof in `THEOREMS_AND_PROOFS.md` now carries the optimal-set
  and least-element argument of the manuscript, Theorem 2 its dimensions and the
  nonterminal-user remark, and Proposition 2 states when Stage 3 is redundant.

## v0.5.1

The changes made for the third review round.

- `bench/robustness_suite.py` was added: 200 generated instances in seven
  families (random capacities, source-binding, edge-binding, missing records,
  deep chains, weight variation and degenerate cases) are solved from a fixed
  seed and every instance is checked against the closed form, the operator and
  node balance representations, the physical capacities, the Stage-1 floor, the
  Stage-2 objective and the Stage-3 optimum. The suite reports the worst
  residual of each gate rather than a pass flag;
- `bench/weight_sweep.py` was added: it sweeps the Stage-2 weight ratio
  geometrically over the small benchmark and applies three auditable weighting
  rules to the surveyed canal, reporting that the Stage-1 guarantee and the
  realized minimum service ratio are invariant under all of them while the
  Stage-2 and Stage-3 optima move;
- `figure_style.canal_scheme_layout` was added and is now used for a surveyed
  network of more than fifteen nodes: the network is drawn in the form of the
  linear canal scheme that the operating organisation itself uses, with the main
  canal as a horizontal axis, every node at its surveyed chainage along that
  axis, and each offtake on the bank from which it really takes water, the right
  bank above and the left bank below. `figure_style` draws it with lead-offs
  whose feet are the true tap points on the canal and with vertical offtake
  identifiers, as in the operator's own drawing; where two offtake points lie
  within a fraction of a per cent of the canal length of each other, only the
  label end of the lead-off is displaced along its bank, by a two-pass spread
  that preserves the along-canal order and stays inside the canal, so the bank
  and the order of every offtake remain exactly those of the survey. On the
  36-node canal the surveyed coordinates themselves placed consecutive offtakes
  too close together for their identifiers to be set at any printable figure
  width; the scheme keeps the hydraulic content and makes all 36 node
  identifiers and all 35 reach identifiers legible. The colour legend,
  previously drawn only on the small benchmarks, is now drawn on every
  rooted-tree figure. No edge is added or removed, and the small benchmarks are
  drawn exactly as before, byte for byte.

## v0.5.0

- the reporting figures were revised in response to peer review: the rooted-tree
  figure now typesets identifiers as mathematical symbols, draws directed
  reaches as arrows and colour-codes source, junction and terminal nodes; the
  profile figure keeps coincident Stage-3 curves visible by decreasing the line
  width from user to user and splits many-user benchmarks into a Stage-2 and a
  Stage-3 panel with a full colour legend; the two matrix-pattern panels are
  drawn by one routine so that they share cell size, typography and a
  positive/negative colour code, and are labelled with node, edge and user
  identifiers instead of bare indices;
- the colour code and the drawing primitives were moved into
  `src/appliedmath_lexflow/figure_style.py`, which the reporting pipeline and
  the desktop application now share: the network and the service-ratio profile
  shown interactively by `main.py` carry the same node-role colours, stage
  colours, markers, layout and mathematical labels as the published figures,
  so an on-screen plot and the corresponding figure of the article cannot
  diverge;
- the pooled operator-versus-node-balance agreement figure now covers exactly
  the benchmarks reported in the exact-verification table, that is, the
  synthetic networks; the surveyed canal carries flows three orders of
  magnitude larger and, pooled in, compressed every synthetic point into the
  origin. The all-benchmark panel is still written, under
  `figure_4_operator_balance_agreement_all_benchmarks`;
- `bench/scale_timing.py` was added: it reports the wall-clock time and peak
  working memory of the closed-form Stage-1 evaluation against the equivalent
  sparse HiGHS Stage-1 LP over the Appendix A scaling generator, as the minimum
  over repeated runs after a warm-up;
- release metadata was raised to v0.5.0 across the project files.

## v0.4.1

- all optimal-value stars use GitHub MathJax-safe `\ast` notation;
- the experiment protocol now checks Stage-2 objective preservation with the
  same two-sided absolute residual used by the implementation;
- the stale reference to a private Word manuscript was removed from the public
  model index;
- a regression gate now checks Markdown math delimiters, braces, raw asterisks,
  fenced blocks, and internal links;
- the pinned dependency record now matches the environment recorded in the run
  manifest, which now also records the Excel writer version;
- release-version, author, dependency, and documentation metadata are checked
  automatically for cross-file consistency.

## v0.4.0

- Stage-2 variation reporting was corrected: $61.9\%$ is now labelled the
  worst-to-best range reduction, while the current $0.75\to0.40$ vertex change
  is reported as the solver-specific $46.7\%$ observation;
- the price-of-fairness pair now uses the same service weights in both LPs;
- leximin computation was replaced by exact rational progressive filling for
  the nonnegative packing model;
- the five deterministic scale instances are generated and verified by a
  path-sparse HiGHS formulation, eliminating the stale $0.72$ table;
- input validation now enforces a nonempty active-record set and leaf terminals;
- verification manifests now contain computed, two-sided preservation gates
  instead of hard-coded pass flags.

## v0.3.0

- мақола ва модель мустақил тадқиқот сифатида қайта позицияланди;
- ташқи ёки режалаштирилмаган нашрларга оид барча ички ишоралар олиб ташланди;
- марказий теоремалар асосий мақолада сақланди;
- solver толеранслари ва файл-level репродуктивлик тафсилотлари Қўшимча материалга ажратилди;
- адабиётлар шарҳи 26 та манбагача кенгайтирилди;
- GUI ва package metadata версияси `0.3.0` га янгиланди.

## v0.2.0

- desktop GUI, ягона `main.py` router ва backend integration test қўшилди.

## v0.1.0

- loss-aware граф оператори;
- Stage-1 ёпиқ формуласи;
- оператор–баланс эквивалентлиги;
- уч босқичли детерминистик лексикографик LP;
- бешта rational benchmark ва reproducible reporting pipeline тайёрланди.
