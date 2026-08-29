from pathlib import Path


ROOT = Path(__file__).parents[1]


def markdown_lines_outside_fences(path: Path):
    in_fence = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            yield line_number, line


def test_markdown_uses_github_math_delimiters():
    unsupported = []
    unbalanced = []

    for path in ROOT.rglob("*.md"):
        delimiters = 0
        for line_number, line in markdown_lines_outside_fences(path):
            stripped = line.strip()
            if stripped in {r"\[", r"\]"}:
                unsupported.append(f"{path.relative_to(ROOT)}:{line_number}")
            if stripped == "$$":
                delimiters += 1
        if delimiters % 2:
            unbalanced.append(str(path.relative_to(ROOT)))

    assert not unsupported, "unsupported display-math delimiters: " + ", ".join(unsupported)
    assert not unbalanced, "unbalanced $$ delimiters: " + ", ".join(unbalanced)
