# AppliedMath LexFlow мустақил илмий лойиҳаси

Ушбу репозиторий *AppliedMath* журнали учун тайёрланаётган мустақил илмий мақоланинг математик ва ҳисоблаш муҳитидир. Лойиҳа йўқотишли ва қуввати чекланган йўналтирилган дарахт тармоқларида детерминистик уч босқичли лексикографик тақсимот моделини таҳлил қилади.

## Илмий чегара

Лойиҳада фақат аниқ берилган детерминистик параметрлар ва rooted-tree
benchmark’лар ишлатилади. Аналитик suite кичик, алоҳида scale suite эса 500
истеъмолчи ва 1022 қиррагача боради. Қуйидагилар модель таркибига кирмайди:

- сценарийли оптималлаштириш;
- стохастик модел;
- робаст оптималлаштириш;
- эҳтимол тақсимоти, uncertainty set ёки chance constraint;
- қайта қарор қабул қилишга асосланган recourse.

Бешта кичик синтетик benchmark математик хоссаларни алоҳида текшириш учун
қурилган. Gone Abat Jap instance очиқ маълумотлар асосидаги детерминистик
controlled scenario. У тарихий танқислик, field calibration ёки муайян
ирригация тизимининг эксплуатацион натижаси сифатида талқин қилинмайди.

Лойиҳанинг асосий назарий натижалари:

1. Stage 1 max–min адолат оптимумининг ёпиқ ифодаси;
2. йўқотишли граф оператори билан тугун–қирра баланси формулировкасининг эквивалентлиги ва оқим ечимининг ягоналиги;
3. уч босқичли лексикографик ечимнинг юқори устувор мақсадларни сақлаш хоссалари.

## Биринчи марта ўрнатиш

VS Code’да лойиҳа илдизини очинг. PowerShell терминалида:

```powershell
python -m venv my-env
my-env\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`run_manifest.json`да қайд этилган айнан аудит қилинган dependency муҳитини
қайта яратиш учун охирги буйруқ ўрнига қуйидагиларни бажаринг:

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
```

Пакет коди янгилангандан кейин editable installation буйруғини қайта бажариш тавсия этилади:

```powershell
python -m pip install -e ".[dev]"
```

## Асосий desktop GUI

Лойиҳанинг ягона асосий файли:

```text
main.py
```

GUI’ни ишга тушириш:

```powershell
python main.py
```

GUI қуйидагиларни бажаради:

- **Тил / Language** менюси ёки `Ctrl+L` орқали Ўзбекча ва English ўртасида
  solver натижасини ўзгартирмасдан алмашиш;
- "Файл → Тармоқ очиш" (ёки бошқарув панелидаги "Очиш…" тугмаси) орқали `Data/benchmarks/` папкасидан истаган `.json` benchmark файлини стандарт ОС файл танлаш ойнаси билан очиш;
- Stage 1, Stage 2 ва Stage 3 ни умумий ҳисоблаш ядросида ечиш;
- ёпиқ $\lambda^{\ast}$ ва HiGHS LP натижасини таққослаш;
- уч босқич KPI’лари ва давр–истеъмолчи тақсимотларини кўрсатиш;
- истеъмолчилар учун Stage 1–2–3 вақт профилларини чизиш;
- тармоқ топологиясини кўрсатиш (benchmark ҳақиқий geometрик координаталарга эга бўлса, шулардан фойдаланилади);
- оператор–тугун баланси, физик амалга оширилиш ва лексикографик сақланиш текширувларини PASS/FAIL кўринишида бериш;
- жорий benchmark натижаларини CSV’га экспорт қилиш;
- `pytest` тестларини интерфейсдан бажариш;
- мақола учун CSV жадваллар, figure-data ва PNG расмларни (ҳар бир benchmark ўз алоҳида папкасида) қайта яратиш;
- `results/` папкасидаги натижа файлларини кўриш ва очиш.

Батафсил йўриқнома: [`DESKTOP_GUI_UZ.md`](DESKTOP_GUI_UZ.md).

## Асосий файлнинг бошқа режимлари

Битта benchmark’ни терминалда босқичма-босқич кўриш:

```powershell
python main.py demo --benchmark temporal_lexicographic
```

Мақола учун барча жадвал ва расмларни қайта яратиш:

```powershell
python main.py analysis
```

Қўшимча launcher’лар:

```powershell
python run_demo.py --benchmark temporal_lexicographic
python run_analysis.py
python run_desktop.py
```

Пакет ўрнатилгандан кейин:

```powershell
appliedmath-lexflow
appliedmath-lexflow-gui
appliedmath-lexflow-demo --benchmark temporal_lexicographic
appliedmath-lexflow-analysis
```

## VS Code

`Terminal → Run Task` менюсида:

- `Setup: Install project in selected interpreter`;
- `GUI: Start desktop application`;
- `Demo: Step-by-step temporal benchmark`;
- `Analysis: Generate article results`;
- `Test: Run pytest`.

Debug учун:

```text
Run and Debug → AppliedMath: Desktop GUI
```

VS Code interpreter сифатида `my-env\Scripts\python.exe` танланган бўлиши керак.

## GitHub’даги очиқ репозиторий таркиби

```text
Model/                       математик модель, теоремалар ва исботлар
Data/benchmarks/             детерминистик rooted-tree benchmark’лар
Data/synthetic_*.json        scale-текширув учун детерминистик instance
src/                         Python пакети ва desktop GUI
tests/                       автоматик математик ва дастурий текширувлар
results/tables/csv/          Git’да сақланадиган ихчам манба жадваллар (table_1..10, A3..A5)
results/manifests/           муҳит, версия ва SHA-256 provenance маълумотлари
results/timing/              компьютерга боғлиқ вақт ўлчовлари (bench script'лари)
results/perturbation/        controlled scenario пертурбация таҳлили (bench script)
bench/                       қўшимча таҳлилларнинг буйруқ сатри script'лари
.github/workflows/           GitHub Actions автоматик текшируви
```

Очиқ Git таркибида ихчам CSV манба жадваллари ва provenance маълумотлари
сақланади. Қуйидаги буйруқ бажарилганда тўлиқ локал натижа дарахти — 600 dpi
PNG расмлар, figure-source CSV файллар, Excel нусхалар ва ҳар бир benchmark учун
алоҳида натижа папкалари — қайта яратилади:

```powershell
python main.py analysis
```

Масалан, шу жараёнда
`results/gone_abat_jap/figures/figure_1_tree.png` ҳамда бошқа benchmark
расмлари локал равишда ҳосил қилинади.

**CSV ва Excel:** CSV манба жадвал Git’да сақланади, унга мос Excel нусха эса
таҳлил буйруғи орқали локал яратилади:

```text
results/tables/csv/table_1_closed_form_verification.csv     ← кейинчалик дастурий ишлов бериш учун
results/tables/excel/table_1_closed_form_verification.xlsx  ← фойдаланувчи учун қулай, тўғридан-тўғри очиш мумкин
```

## Автоматик текшириш

```powershell
python -m pytest -p no:cacheprovider
```

Жорий версияда:

- 76/76 автоматик тест PASS;
- 6 та детерминистик benchmark: 5 exact синтетик ва 1 controlled scenario;
- $\max|\lambda^{\mathrm{LP}}-\lambda^{\mathrm{cf}}|\approx1.11\times10^{-16}$;
- exact operator–balance фарқи $0$;
- exact node-balance residual $0$;
- temporal benchmark’да Stage-2 optimal face бўйича
  $\Omega\in[0.40,1.05]$, Stage 3 эса инвариант minimum $0.40$ ни беради;
- жорий HiGHS танлаган $0.75$ нуқтадан кузатилган камайиш $46.7\%$;
  $61.9\%$ эса фақат $1.05$ дан $0.40$ гача worst-to-best диапазон
  қисқариши бўлиб, ҳар қандай Stage-2 ечимидан кафолатланган камайиш эмас;
- бешта репродуктив scale test’да (500 истеъмолчи ва 1022 қиррагача)
  $\lambda^{\ast}=0.60$, sparse HiGHS ечими ёпиқ формула билан floating-point
  аниқлигида мос;
- $\lambda^{\ast}=0.60$ ва Stage-2 қониқиши сонли толеранс доирасида сақланган.
- тасодифий 400 та инстанциянинг ҳаммасида §2.9 чегаралари бажарилади ва
  ёпиқ формула кўрсатган тор жой Stage-1 LP нинг ўзи орқали тасдиқланади.

## Қўшимча таҳлиллар

Бу таҳлиллар учинчи тақриз раундига жавобан қўшилган. Детерминистик қисми
`python run_analysis.py` таркибида; компьютерга боғлиқ ёки узоқ ишлайдиган
учтаси алоҳида script бўлиб, уларнинг натижасини `run_analysis.py` сақлаб
қолади ва манифестга ёзади.

| Таҳлил | Буйруқ | Натижа |
|---|---|---|
| Тасодифий синов тўплами, тор жойни аниқлаш, Stage-3 фаоллиги | `run_analysis.py` (экранда: `python bench/robustness_suite.py`) | `results/tables/csv/table_A3_robustness_*.csv` |
| Муқобил тақсимот қоидалари билан солиштириш | `run_analysis.py` | `results/tables/csv/table_9_rule_comparison*.csv` |
| Stage 3 нинг муқобил силлиқлик мезонлари ва блокларга хос чекловлар | `run_analysis.py` | `results/tables/csv/table_10_*.csv` |
| Вазнлар таҳлили: бешта қоида, ютган ва ютқазган блоклар (синтетик вазнлар) | `run_analysis.py` (экранда: `python bench/weight_sweep.py`) | `results/tables/csv/table_A4_*.csv`, `table_A5_*.csv` |
| Controlled scenario параметрлари пертурбацияси | `python bench/perturbation.py` | `results/perturbation/` |
| Ёпиқ формула ва LP вақти, босқичма-босқич | `python bench/scale_timing.py` | `results/timing/scale_timing*.csv`, `environment.json` |
| Ҳар бир қоиданинг ишлаш вақти | `python bench/compare_rules.py` | `results/timing/rule_comparison_timing.csv` |

Пертурбация таҳлили детерминистик моделни ўзгартирилган маълумотлар билан
қайта ечади; у натижаларнинг сезгирлик таҳлили, стохастик ёки робаст
формулировка эмас.


## Мақоладаги жадвал ва расмларнинг манба файллари

Файл номлари пакетнинг ўз рақамлашига амал қилади. Мақоладаги жадвал рақами
билан файл номи мослиги README.md даги "Where each table and figure of the
manuscript comes from" жадвалида тўлиқ келтирилган (масалан, мақоладаги
Table 4 → `table_5_invariant_variation_and_price_of_fairness.csv`, Table 8 →
`table_A3_robustness_suite.csv`, Table 10 →
`results/perturbation/csv/perturbation_summary.csv`, Table A2 →
`table_A2_controlled_scenario_periods.csv`, Table A6 →
`table_10_smoothness_criteria.csv`).

## Tkinter текшируви

GUI Python стандарт `tkinter` кутубхонасига асосланган. Текшириш:

```powershell
python -m tkinter
```

Тест ойнаси очилса, GUI муҳити тайёр. `No module named tkinter` хатосида Python installer орқали `Tcl/Tk and IDLE` компонентини қўшинг.

## Мақола ва қўшимча материал

Очиқ репозиторийда код, математик ҳужжатлар, benchmark маълумотлари, тестлар,
ихчам натижа жадваллари ва репродуктивлик метамаълумотлари сақланади. `0.5.2`
версияси GitHub’даги
[`v0.5.3` release](https://github.com/Adilbaygh/appliedmath-lexflow_v1_0_0/releases/tag/v0.5.3)
билан белгиланади. Мақоланинг ўзбекча ишчи нусхаси, лицензияланган журнал
шаблони ва ички аудит файллари очиқ GitHub репозиторийсига ҳамда очиқ
дастурий архивга киритилмайди. Ҳар бир тегланган release Zenodo'да
архивланади; концепция DOI
[10.5281/zenodo.22669687](https://doi.org/10.5281/zenodo.22669687) доимо
энг охирги версияга олиб боради, мақоланинг Data Availability Statement
қисмида эса шу release'нинг версия DOI'си кўрсатилади.
