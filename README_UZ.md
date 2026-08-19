# AppliedMath LexFlow мустақил илмий лойиҳаси

Ушбу репозиторий *AppliedMath* журнали учун тайёрланаётган мустақил илмий мақоланинг математик ва ҳисоблаш муҳитидир. Лойиҳа йўқотишли ва қуввати чекланган йўналтирилган дарахт тармоқларида детерминистик уч босқичли лексикографик тақсимот моделини таҳлил қилади.

## Илмий чегара

Лойиҳада фақат аниқ берилган детерминистик параметрлар ва кичик rooted-tree benchmark’лар ишлатилади. Қуйидагилар модель таркибига кирмайди:

- сценарийли оптималлаштириш;
- стохастик модел;
- робаст оптималлаштириш;
- эҳтимол тақсимоти, uncertainty set ёки chance constraint;
- қайта қарор қабул қилишга асосланган recourse.

Кичик синтетик benchmark’лар математик хоссаларни алоҳида текшириш учун қурилган. Улар тарихий дала маълумотлари, field calibration ёки муайян ирригация тизимининг эксплуатацион натижаси сифатида талқин қилинмайди.

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

- "Файл → Тармоқ очиш" (ёки бошқарув панелидаги "Очиш…" тугмаси) орқали `Data/benchmarks/` папкасидан истаган `.json` benchmark файлини стандарт ОС файл танлаш ойнаси билан очиш;
- Stage 1, Stage 2 ва Stage 3 ни умумий ҳисоблаш ядросида ечиш;
- ёпиқ $\lambda^*$ ва HiGHS LP натижасини таққослаш;
- уч босқич KPI’лари ва давр–истеъмолчи тақсимотларини кўрсатиш;
- истеъмолчилар учун Stage 1–2–3 вақт профилларини чизиш;
- тармоқ топологиясини кўрсатиш (benchmark ҳақиқий geometрик координаталарга эга бўлса, шулардан фойдаланилади);
- оператор–тугун баланси, физик амалга оширилиш ва лексикографик сақланиш текширувларини PASS/FAIL кўринишида бериш;
- жорий benchmark натижаларини CSV’га экспорт қилиш;
- `pytest` тестларини интерфейсдан бажариш;
- мақола учун CSV жадваллар, figure-data ва PNG расмларни (ҳар бир benchmark ўз алоҳида папкасида) қайта яратиш;
- `results/` папкасидаги натижа файлларини кўриш ва очиш.

Батафсил йўриқнома: `DESKTOP_GUI_UZ.md`.

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

## Натижа папкалари

```text
results/tables/                    benchmark’лар ўртасида қиёсловчи жадваллар (table_1..4)
results/figures/                   benchmark’га боғлиқ бўлмаган назарий расмлар (600 dpi PNG)
results/figure_data/               шу назарий расмларнинг манба жадваллари
results/<benchmark_номи>/figures/       ушбу benchmark’нинг ўз расмлари (тармоқ дарахти, профиль,
                                    матрица нақшлари, оператор мослиги — 600 dpi PNG)
results/<benchmark_номи>/figure_data/   ушбу benchmark’нинг ўз расмлари учун манба жадваллари
results/manifests/                 муҳит, версия ва SHA-256 manifest
results/gui_exports/               GUI орқали экспорт қилинган жорий benchmark жадваллари
```

Яъни ҳар бир тармоқ (benchmark)нинг ўз натижалари (`figure_1_tree.png`, `figure_5_profiles.png`,
`figure_6_matrix.png`, `figure_7_matrix.png`, `figure_4_operator_balance_agreement.png` ва уларнинг
манба жадваллари) шу тармоқнинг номи билан аталган алоҳида папкада сақланади — мас.
`results/gone_abat_jap/figures/figure_1_tree.png`.

**CSV ва Excel:** юқоридаги ҳар бир жадвал-папка (`tables/`, `figure_data/`, шунингдек ҳар бир
benchmark'нинг ўз `figure_data/`си) ичида жадваллар икки марта, мос номдаги алоҳида папкаларда
сақланади:

```text
results/tables/csv/table_1_closed_form_verification.csv     ← кейинчалик дастурий ишлов бериш учун
results/tables/excel/table_1_closed_form_verification.xlsx  ← фойдаланувчи учун қулай, тўғридан-тўғри очиш мумкин
```

## Автоматик текшириш

```powershell
python -m pytest -p no:cacheprovider
```

Жорий версияда:

- 7/7 автоматик тест PASS;
- 5 та детерминистик benchmark;
- $\max|\lambda^{\mathrm{LP}}-\lambda^{\mathrm{cf}}|\approx1.11\times10^{-16}$;
- exact operator–balance фарқи $0$;
- exact node-balance residual $0$;
- temporal benchmark’да $\Omega$ қиймати $0.75$ дан тахминан $0.40$ гача камайган;
- $\lambda^*=0.60$ ва Stage-2 қониқиши сонли толеранс доирасида сақланган.

## Tkinter текшируви

GUI Python стандарт `tkinter` кутубхонасига асосланган. Текшириш:

```powershell
python -m tkinter
```

Тест ойнаси очилса, GUI муҳити тайёр. `No module named tkinter` хатосида Python installer орқали `Tcl/Tk and IDLE` компонентини қўшинг.

## Мақола ва қўшимча материал

Мақоланинг ўзбек кирилл тилидаги ишчи матни `Paper/AppliedMath_Manuscript_Draft_UZ.docx` файлида, ҳисоблаш тафсилотлари эса `Paper/AppliedMath_Supplementary_Material_UZ.docx` файлида сақланади. Адабиётлар рўйхати тармоқ оқимлари, ирригацияни оптималлаштириш, адолатли ресурс тақсимоти ва лексикографик дастурлашга оид 26 та манбани қамраб олади.
