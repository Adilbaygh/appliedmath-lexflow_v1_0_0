from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from appliedmath_lexflow.reporting import generate_results

SOURCE_DATA = Path(__file__).resolve().parents[1] / "Data" / "benchmarks"


def _hash_outputs(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for path in sorted((root / "results").rglob("*")):
        if not path.is_file() or "manifests" in path.parts:
            continue
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def test_generated_article_assets_are_byte_reproducible(tmp_path: Path) -> None:
    data_dir = tmp_path / "Data" / "benchmarks"
    data_dir.mkdir(parents=True)
    for source in SOURCE_DATA.glob("*.json"):
        shutil.copy2(source, data_dir / source.name)

    generate_results(tmp_path)
    first = _hash_outputs(tmp_path)
    generate_results(tmp_path)
    second = _hash_outputs(tmp_path)
    assert first == second
