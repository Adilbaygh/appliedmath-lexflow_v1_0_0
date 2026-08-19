# `ModuleNotFoundError: appliedmath_lexflow` хатосини тузатиш

Лойиҳа `src`-layout асосида қурилган. Тавсия этиладиган ишга тушириш тартиби:

```powershell
& ".\my-env\Scripts\python.exe" -m pip install --upgrade pip
& ".\my-env\Scripts\python.exe" -m pip install -e ".[dev]"
& ".\my-env\Scripts\python.exe" -c "import appliedmath_lexflow; print(appliedmath_lexflow.__version__)"
& ".\my-env\Scripts\python.exe" ".\run_demo.py" --benchmark temporal_lexicographic
```

`v0.1.1` да `run_demo.py` ва `run_analysis.py` `src/` папкасини автоматик қўшади, шунинг учун улар editable installation бажарилмасдан ҳам тўғридан-тўғри ишлайди. Бироқ `pytest`, VS Code debugging ва GitHub иш жараёни учун `pip install -e ".[dev]"` тавсия этилади.
