from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from appliedmath_lexflow import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_release_metadata_is_consistent() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = pyproject["project"]
    version = project["version"]
    assert __version__ == version

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    citation_version = re.search(r"(?m)^version:\s*([^\s]+)\s*$", citation)
    assert citation_version is not None
    assert citation_version.group(1) == version

    citation_authors = [
        f"{given} {family}"
        for family, given in re.findall(
            r"family-names:\s*([^\r\n]+)\r?\n\s+given-names:\s*([^\r\n]+)",
            citation,
        )
    ]
    assert citation_authors == [author["name"] for author in project["authors"]]

    expected_release = f"releases/tag/v{version}"
    assert expected_release in (ROOT / "README.md").read_text(encoding="utf-8")
    assert expected_release in (ROOT / "README_UZ.md").read_text(encoding="utf-8")
    assert f"## v{version}" in (ROOT / "Model" / "MODEL_CHANGELOG.md").read_text(
        encoding="utf-8"
    )
    assert f"v{version}" in (ROOT / "requirements-lock.txt").read_text(
        encoding="utf-8"
    )

    locked = {}
    for line in (ROOT / "requirements-lock.txt").read_text(encoding="utf-8").splitlines():
        if "==" in line and not line.lstrip().startswith("#"):
            name, pinned = line.split("==", maxsplit=1)
            locked[name] = pinned

    manifest = json.loads(
        (ROOT / "results" / "manifests" / "run_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["dependencies"]
    for name, recorded in manifest["dependencies"].items():
        assert locked.get(name) == recorded
