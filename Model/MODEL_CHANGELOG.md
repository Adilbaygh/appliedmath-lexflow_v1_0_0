# Model development log

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
