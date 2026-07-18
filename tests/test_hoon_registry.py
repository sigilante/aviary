"""SPEC-DESK.md §7: registry cross-test between the Python kernel
(aviary_kernel/birds.py, the verified reference) and the Hoon engine's
hand-written registry (desk/lib/aviary.hoon).

The Hoon registry is a strictly formatted literal (SPEC-DESK.md §4.2):
one bird per line, exactly

    ['NAME' 'DISP' ARITY "RULE"]

within the `++  birds` arm's `:~ ... ==` list. That format is itself a
contract -- a registry line that doesn't match ROW_RE is a hard test
failure, not a line to skip.

Both sides derive their comparison tuples from their own actual data:
the Hoon side's rule text *is* its source of truth (SPEC-DESK.md §4.2:
"the source of truth is the text, so the cross-test and the code cannot
disagree"); the Python side pretty-prints each Bird's `rule` Term with
the default (identity) display function, which is exactly ASCII since
rule bodies only ever contain formal-variable atoms (a, b, c, ...), never
registry names -- so no display-name mapping is needed to get a
canonical-ASCII string out of it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from aviary_kernel.birds import BIRDS
from aviary_kernel.terms import pretty

HOON_LIB = Path(__file__).resolve().parent.parent / "desk" / "lib" / "aviary.hoon"

# One registry row, exactly: ['NAME' 'DISP' ARITY "RULE"]. Names may
# contain a backslash-escaped apostrophe (Hoon cord-literal escaping, for
# KM' and W'); RULE is free-form except for a literal double quote.
ROW_RE = re.compile(
    r"^\[\'((?:[^\'\\]|\\.)*)\'\s+\'((?:[^\'\\]|\\.)*)\'\s+(\d+)\s+\"([^\"]*)\"\]$"
)

Y_SKI_RE = re.compile(r'^\+\+\s+y-ski\s+"([^"]*)"$')


def _unescape_cord(s: str) -> str:
    """Undo Hoon single-quote-cord escaping (only \\' is ever produced by
    our registry, but handle \\\\ generically for safety)."""
    return s.replace("\\'", "'").replace("\\\\", "\\")


def _hoon_source_lines() -> list[str]:
    assert HOON_LIB.is_file(), f"expected {HOON_LIB} to exist"
    return HOON_LIB.read_text(encoding="utf-8").split("\n")


def _birds_block_lines(lines: list[str]) -> list[str]:
    """Lines strictly between `++  birds` and its closing `==` (SPEC-
    DESK.md §4.2's `:~ ... ==` list), with the row content only -- the
    arm header, the `^-  (list bird)` cast, and the `:~`/`==` delimiters
    themselves are not row lines."""
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "++  birds":
            start = i
            break
    assert start is not None, "desk/lib/aviary.hoon has no `++  birds` arm"

    rows: list[str] = []
    in_list = False
    for line in lines[start + 1:]:
        stripped = line.strip()
        if not in_list:
            if stripped.startswith(":~"):
                in_list = True
                rest = stripped[2:].strip()
                if rest:
                    rows.append(rest)
            continue
        if stripped == "==":
            return rows
        rows.append(stripped)
    raise AssertionError("desk/lib/aviary.hoon's `++  birds` list has no closing `==`")


def _parse_hoon_registry() -> set[tuple[str, str, int, str]]:
    lines = _hoon_source_lines()
    rows = _birds_block_lines(lines)
    out: set[tuple[str, str, int, str]] = set()
    bad: list[str] = []
    for row in rows:
        m = ROW_RE.match(row)
        if m is None:
            bad.append(row)
            continue
        name, disp, arity, rule = m.groups()
        out.add((_unescape_cord(name), _unescape_cord(disp), int(arity), rule))
    if bad:
        raise AssertionError(
            "desk/lib/aviary.hoon `++  birds` row(s) did not match the "
            f"required §4.2 format ['NAME' 'DISP' ARITY \"RULE\"]: {bad!r}"
        )
    return out


def _parse_hoon_y_ski() -> str:
    lines = _hoon_source_lines()
    for line in lines:
        m = Y_SKI_RE.match(line.strip())
        if m is not None:
            return m.group(1)
    raise AssertionError("desk/lib/aviary.hoon has no `++  y-ski  \"...\"` line")


def _python_registry() -> set[tuple[str, str, int, str]]:
    return {(b.name, b.display, b.arity, pretty(b.rule)) for b in BIRDS}


def test_hoon_registry_rows_match_python_exactly():
    """Hard-fail (never skip) on any bird present on one side only, or
    whose (name, display, arity, rule-text) tuple differs."""
    hoon = _parse_hoon_registry()
    python = _python_registry()

    only_in_hoon = hoon - python
    only_in_python = python - hoon

    assert not only_in_hoon and not only_in_python, (
        "Hoon registry (desk/lib/aviary.hoon) and Python registry "
        "(aviary_kernel/birds.py) disagree.\n"
        f"Only in Hoon:   {sorted(only_in_hoon)}\n"
        f"Only in Python: {sorted(only_in_python)}"
    )


def test_hoon_registry_row_count_is_fifty():
    """SPEC.md §5.2's aviary is exactly the 50 standard birds."""
    assert len(_parse_hoon_registry()) == 50 == len(BIRDS)


def test_hoon_y_ski_matches_python():
    """Y's explicit S/K/I override string (SPEC-DESK.md §4.2's bullet on
    Y) must match byte-for-byte between the two sides, since bracket
    abstraction diverges on Y and both engines rely on this exact text."""
    y = next(b for b in BIRDS if b.name == "Y")
    assert y.ski is not None, "Python's Y bird has no ski override"
    python_ski = pretty(y.ski)
    hoon_ski = _parse_hoon_y_ski()
    assert hoon_ski == python_ski


@pytest.mark.parametrize("b", BIRDS, ids=lambda b: b.name)
def test_every_python_bird_is_in_hoon_registry(b):
    """Per-bird parametrization (SPEC-DESK.md §7: "hard-fail... on a bird
    present on one side only") so a single missing/mismatched bird shows
    up as one named failing test, not a single opaque set-diff."""
    hoon = _parse_hoon_registry()
    row = (b.name, b.display, b.arity, pretty(b.rule))
    assert row in hoon, f"{b.name} missing/mismatched in desk/lib/aviary.hoon: {row}"
