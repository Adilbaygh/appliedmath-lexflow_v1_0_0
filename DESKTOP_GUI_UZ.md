# AppliedMath LexFlow Desktop GUI — Ўзбекча / English

Desktop интерфейс `main.py` орқали ишга тушади ва `src/appliedmath_lexflow/` ичидаги умумий детерминистик ҳисоблаш ядросидан фойдаланади.

Интерфейс икки тилда ишлайди. Менюдаги **Тил / Language** бўлими ёки
`Ctrl+L` орқали **Ўзбекча** ва **English** ўртасида алмашиш мумкин. Тилни
алмаштириш solver параметрлари ёки сонли натижаларни ўзгартирмайди.

GUI фақат аниқ параметрларга эга rooted-tree benchmark’ларни ечади. Сценарийли, стохастик ва робаст оптималлаштириш ишлатилмайди. Натижалар синтетик математик мисолларга тегишли бўлиб, дала валидацияси ёки муайян канал тизимининг эксплуатацион баҳоси ҳисобланмайди.

## Ишга тушириш

```powershell
cd "<project-folder>"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
python -m pip install -e ".[dev]"
python main.py
```

## Тармоқ танлаш

Дастур очилганда ҳеч қандай тармоқ юкланмаган бўлади ("тармоқ танланмади"). Тармоқни танлаш учун:

- бошқарув панелидаги **"Очиш…"** тугмасини босинг, ёки
- **Файл → Тармоқ очиш** менюсини танланг (F5 эса аввал очилган тармоқни қайта ҳисоблайди).

Иккаласи ҳам стандарт ОС файл танлаш ойнасини `Data/benchmarks/` папкасида очади; танланган `.json` файл ечилиб, ёрлиқда унинг номи кўринади.

## Асосий вкладкалар

1. **Умумий натижа** — $\lambda^{\mathrm{cf}}$, $\lambda^{\mathrm{LP}}$, Stage-2 қониқиши, Stage-3 вариацияси ва PASS/FAIL ҳолати.
2. **Тақсимотлар** — ҳар бир давр–истеъмолчи ёзуви учун Stage 1–3 нисбатлари ва вақт профиллари.
3. **Верификация** — closed-form/LP фарқи, operator–balance фарқи, node residual ва сақланиш gate’лари.
4. **Тармоқ** — танланган benchmark дарахти.
5. **Натижа файллари** — CSV, figure-data ва расмларни кўриш.
6. **Журнал** — ҳисоблаш ва тест хабарлари.

## Қўшимча вазифалар

- `Мақола натижаларини яратиш` — `Data/benchmarks/` ичидаги ҳар бир benchmark учун ўз алоҳида папкасида (`results/<номи>/figures/`, `results/<номи>/figure_data/`, фақат PNG) ва умумий қиёсловчи жадвалларни (`results/tables/`) қайта яратади;
- `Тестларни ишга тушириш` — `pytest` ни бажаради;
- `CSV/Excel экспорт` — жорий benchmark тақсимотларини `results/gui_exports/csv/` ва `results/gui_exports/excel/` га (иккала форматда ҳам) ёзади;
- `Натижалар папкасини очиш` — output каталогини очади.

## Текшириш

```powershell
python -m pytest -p no:cacheprovider
python -m tkinter
```

Кутиладиган натижа: барча тестлар `passed`; аниқ сони янги илмий gate’лар
қўшилганда ўзгариши мумкин.

## English quick start

The desktop application and the publication pipeline call the same
`appliedmath_lexflow` solver package. Start it with `python main.py`, then choose
**Language / Тил → English** (or press `Ctrl+L`). Open any JSON benchmark under
`Data/benchmarks/`, solve it, and inspect the Overview, Allocations,
Verification, Network, Result Files, and Log tabs. The boundary statement in
**Help → Model Boundary** is part of the scientific interpretation: the shipped
examples are deterministic synthetic benchmarks, not field validation of a
specific canal system.
