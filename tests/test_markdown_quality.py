from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_FILES = (
    ROOT / "README.md",
    ROOT / "README_UZ.md",
    ROOT / "DESKTOP_GUI_UZ.md",
    *(sorted((ROOT / "Model").glob("*.md"))),
)

DISPLAY_MATH = re.compile(r"(?<!\\)\$\$(.*?)(?<!\\)\$\$", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def _is_escaped(text: str, position: int) -> bool:
    backslashes = 0
    position -= 1
    while position >= 0 and text[position] == "\\":
        backslashes += 1
        position -= 1
    return backslashes % 2 == 1


def _split_fences(text: str) -> tuple[str, list[str], list[str]]:
    prose: list[str] = []
    math_blocks: list[str] = []
    errors: list[str] = []
    fence_marker: str | None = None
    fence_is_math = False
    fenced_lines: list[str] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^\s*(`{3,}|~{3,})(.*)$", line)
        if fence_marker is None:
            if match:
                fence_marker = match.group(1)
                fence_is_math = match.group(2).strip().lower() == "math"
                fenced_lines = []
            else:
                prose.append(line)
            continue

        if match and match.group(1)[0] == fence_marker[0] and len(match.group(1)) >= len(fence_marker):
            if fence_is_math:
                math_blocks.append("\n".join(fenced_lines))
            fence_marker = None
            fence_is_math = False
            fenced_lines = []
        elif fence_is_math:
            fenced_lines.append(line)

    if fence_marker is not None:
        errors.append("unclosed fenced code block")
    return "\n".join(prose), math_blocks, errors


def _extract_math(text: str) -> tuple[list[str], list[str]]:
    expressions = [match.group(1) for match in DISPLAY_MATH.finditer(text)]
    without_display = DISPLAY_MATH.sub("", text)
    errors: list[str] = []

    if len(re.findall(r"(?<!\\)\$\$", text)) % 2:
        errors.append("unmatched $$ display-math delimiter")

    for line_number, line in enumerate(without_display.splitlines(), start=1):
        line = INLINE_CODE.sub("", line)
        positions = [
            index
            for index, char in enumerate(line)
            if char == "$" and not _is_escaped(line, index)
        ]
        if len(positions) % 2:
            errors.append(f"line {line_number}: unmatched inline-math $ delimiter")
            continue
        for start, end in zip(positions[::2], positions[1::2]):
            expressions.append(line[start + 1 : end])

    return expressions, errors


def _math_errors(expression: str) -> list[str]:
    errors: list[str] = []
    stack: list[int] = []
    for index, char in enumerate(expression):
        if char == "{" and not _is_escaped(expression, index):
            stack.append(index)
        elif char == "}" and not _is_escaped(expression, index):
            if not stack:
                errors.append("closing brace has no matching opening brace")
            else:
                stack.pop()
    if stack:
        errors.append("opening brace has no matching closing brace")

    if re.search(r"[\^_]\s*(?:\*|[\^_])", expression):
        errors.append("unsafe or incomplete TeX superscript/subscript token")
    if "*" in expression:
        errors.append("raw * in math; use \\ast to avoid GitHub Markdown interference")
    if len(re.findall(r"\\left\b", expression)) != len(re.findall(r"\\right\b", expression)):
        errors.append("unbalanced \\left and \\right")

    begins = re.findall(r"\\begin\{([^}]+)\}", expression)
    ends = re.findall(r"\\end\{([^}]+)\}", expression)
    if begins != ends:
        errors.append("unbalanced or misordered TeX environments")
    return errors


def _link_errors(path: Path, text: str) -> list[str]:
    errors: list[str] = []
    for raw_target in MARKDOWN_LINK.findall(text):
        target = raw_target.strip()
        if target.startswith("<") and target.endswith(">"):
            target = target[1:-1]
        target = target.split(maxsplit=1)[0]
        parsed = urlsplit(target)
        if parsed.scheme or target.startswith("#"):
            continue
        relative = unquote(parsed.path)
        if relative and not (path.parent / relative).resolve().exists():
            errors.append(f"missing internal link target: {relative}")
    return errors


def test_public_markdown_is_github_safe() -> None:
    failures: list[str] = []
    for path in MARKDOWN_FILES:
        text = path.read_text(encoding="utf-8")
        prose, fenced_math, errors = _split_fences(text)
        expressions, math_parse_errors = _extract_math(prose)
        errors.extend(math_parse_errors)
        expressions.extend(fenced_math)
        for expression in expressions:
            errors.extend(_math_errors(expression))
        errors.extend(_link_errors(path, text))
        failures.extend(f"{path.relative_to(ROOT)}: {error}" for error in errors)

    assert not failures, "\n" + "\n".join(failures)
