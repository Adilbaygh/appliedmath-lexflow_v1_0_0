# Model development log

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
