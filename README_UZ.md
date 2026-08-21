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
results/tables/csv/          Git’да сақланадиган ихчам манба жадваллар (table_1..8)
results/manifests/           муҳит, версия ва SHA-256 provenance маълумотлари
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

- 24/24 автоматик тест PASS;
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

## Tkinter текшируви

GUI Python стандарт `tkinter` кутубхонасига асосланган. Текшириш:

```powershell
python -m tkinter
```

Тест ойнаси очилса, GUI муҳити тайёр. `No module named tkinter` хатосида Python installer орқали `Tcl/Tk and IDLE` компонентини қўшинг.

## Мақола ва қўшимча материал

Очиқ репозиторийда код, математик ҳужжатлар, benchmark маълумотлари, тестлар,
ихчам натижа жадваллари ва репродуктивлик метамаълумотлари сақланади. `0.4.1`
версияси GitHub’даги
[`v0.4.1` release](https://github.com/Adilbaygh/appliedmath-lexflow_v1_0_0/releases/tag/v0.4.1)
билан белгиланади. Мақоланинг ўзбекча ишчи нусхаси, лицензияланган журнал
шаблони, ички аудит файллари ва Mendeley upload workspace очиқ GitHub
репозиторийсига ҳамда очиқ дастурий архивга киритилмайди. Mendeley DOI
берилгандан кейин у архив метамаълумотларига ва мақоланинг Data and Code
Availability Statement қисмига киритилади; ҳозирча шартли DOI ёзилмайди.
