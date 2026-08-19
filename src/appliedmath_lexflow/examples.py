from __future__ import annotations

from pathlib import Path

from .domain import Benchmark
from .io import load_benchmark


def load_all_benchmarks(data_dir: str | Path) -> list[Benchmark]:
    data_dir = Path(data_dir)
    return [load_benchmark(path) for path in sorted(data_dir.glob("*.json"))]
