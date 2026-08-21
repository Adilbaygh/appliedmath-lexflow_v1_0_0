"""Shared helper for writing tabular results in both CSV and Excel.

Every generated table is written twice, side by side in dedicated
subfolders: ``csv/`` (for downstream/automated processing) and ``excel/``
(a convenient, directly readable ``.xlsx`` copy for people).
"""

from __future__ import annotations

import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

# openpyxl unconditionally re-stamps the workbook's <dcterms:modified>
# property with the current wall-clock time inside Workbook.save() (it does
# this itself, after any properties we set are consumed), and Python's
# zipfile.writestr() stamps every archive member with the current time when
# given a bare filename. Left alone, both make repeated runs of the same
# pipeline produce byte-different .xlsx files. _freeze_xlsx() rewrites the
# just-saved archive so every entry and the modified timestamp are pinned,
# matching the deterministic PNG metadata used elsewhere in this project.
_FIXED_EXCEL_DATE = datetime(2000, 1, 1, tzinfo=UTC)
_FIXED_ZIP_DATE_TIME = (2000, 1, 1, 0, 0, 0)
_SOFTWARE_LABEL = "AppliedMath LexFlow"
_MODIFIED_PATTERN = re.compile(
    rb"<dcterms:modified[^>]*>.*?</dcterms:modified>"
)
_MODIFIED_REPLACEMENT = (
    b'<dcterms:modified xsi:type="dcterms:W3CDTF">2000-01-01T00:00:00Z</dcterms:modified>'
)


def _freeze_xlsx(path: Path) -> None:
    """Rewrite an already-saved .xlsx so it is byte-reproducible across runs."""
    with zipfile.ZipFile(path, "r") as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]

    frozen: list[tuple[zipfile.ZipInfo, bytes]] = []
    for info, data in entries:
        if info.filename == "docProps/core.xml":
            data = _MODIFIED_PATTERN.sub(_MODIFIED_REPLACEMENT, data)
        info.date_time = _FIXED_ZIP_DATE_TIME
        info.create_system = 0  # normalize DOS vs. Unix zip metadata across OSes
        frozen.append((info, data))

    # Rebuild beside the workbook and atomically replace it. Reopening the same
    # path for truncating writes can intermittently fail on Windows immediately
    # after openpyxl closes the file (for example while an indexer scans it).
    temporary = path.with_name(f".{path.name}.freeze-tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as target:
        for info, data in frozen:
            target.writestr(info, data)
    temporary.replace(path)


def write_table(
    frame: pd.DataFrame,
    directory: Path,
    stem: str,
    *,
    index: bool = False,
    index_label: str | None = None,
) -> None:
    """Write ``frame`` as ``directory/csv/{stem}.csv`` and ``directory/excel/{stem}.xlsx``."""
    csv_dir = directory / "csv"
    excel_dir = directory / "excel"
    csv_dir.mkdir(parents=True, exist_ok=True)
    excel_dir.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_dir / f"{stem}.csv", index=index, index_label=index_label)

    excel_path = excel_dir / f"{stem}.xlsx"
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        frame.to_excel(writer, index=index, index_label=index_label, sheet_name="Sheet1")
        properties = writer.book.properties
        properties.creator = _SOFTWARE_LABEL
        properties.lastModifiedBy = _SOFTWARE_LABEL
        properties.created = _FIXED_EXCEL_DATE
    _freeze_xlsx(excel_path)
