"""SPEC.md §12 item 1: parser round-trips, minimal parenthesization,
lexer rules (§4)."""

from __future__ import annotations

import pytest

from aviary_kernel.parser import (
    parse_cell, canonicalize, split_statements, is_incomplete, paren_balance,
    ParseError, Magic, Alias, Rule, Expr,
)
from aviary_kernel.terms import pretty


def _roundtrip(src: str) -> str:
    term = parse_cell(src)[0].expr
    return pretty(term)


@pytest.mark.parametrize("src", [
    "S K K",
    "S K (K I)",
    "B M (R M B) B",
    "K ▲ (M M)",
    "▲ 🟢",
    "λx (foo_bar)",
    "(((S)))",
    "S (K S) K",
    "Q₁ a b c",
    "W' x y",
])
def test_roundtrip_parse_pretty(src):
    # parse . pretty == id, modulo whitespace normalization and redundant
    # parens (which pretty() never introduces or requires to re-parse).
    once = _roundtrip(src)
    twice = _roundtrip(once)
    assert once == twice


def test_minimal_parenthesization():
    # Left-nested application never needs parens.
    assert _roundtrip("((S K) (K I))") == "S K (K I)"
    # Right-nested application (arg is itself an application) needs parens.
    assert _roundtrip("S (K (K I))") == "S (K (K I))"
    assert _roundtrip("S K K") == "S K K"


def test_unicode_and_emoji_atoms_are_single_tokens():
    stmts = parse_cell("▲ 🟢")
    expr = stmts[0].expr
    assert pretty(expr) == "▲ 🟢"


def test_multichar_name_is_one_atom_not_application():
    # SKK is one free-variable atom, not three (SPEC.md §4.2).
    stmts = parse_cell("SKK")
    term = stmts[0].expr
    from aviary_kernel.terms import Atom
    assert term == Atom("SKK")


def test_no_single_letter_special_casing():
    # B1 is one token (a bird name); B 1 is two tokens (B applied to a
    # free variable literally named "1").
    from aviary_kernel.terms import Atom, App
    t1 = parse_cell("B1")[0].expr
    assert t1 == Atom("B1")
    t2 = parse_cell("B 1")[0].expr
    assert t2 == App(Atom("B"), Atom("1"))


def test_nested_parens():
    term = parse_cell("(((K)) ((S I) I))")[0].expr
    assert pretty(term) == "K (S I I)"


def test_comment_to_end_of_line():
    stmts = parse_cell("K x y  # this is a comment with (parens)")
    assert len(stmts) == 1
    assert pretty(stmts[0].expr) == "K x y"


def test_comment_only_line_is_skipped():
    stmts = parse_cell("# just a comment\nK x y")
    assert len(stmts) == 1


def test_blank_lines_skipped():
    stmts = parse_cell("\n\nK x y\n\n")
    assert len(stmts) == 1


def test_multiple_statements_per_cell():
    stmts = parse_cell("K x y\nS K K")
    assert len(stmts) == 2
    assert all(isinstance(s, Expr) for s in stmts)


def test_alias_statement():
    stmts = parse_cell("Theta := U U")
    assert len(stmts) == 1
    assert isinstance(stmts[0], Alias)
    assert stmts[0].name_token.canonical == "Theta"
    assert pretty(stmts[0].expr) == "U U"


def test_rule_statement():
    stmts = parse_cell("🟢 x y z -> x (z y)")
    assert len(stmts) == 1
    r = stmts[0]
    assert isinstance(r, Rule)
    assert r.name_token.canonical == "🟢"
    assert [t.canonical for t in r.var_tokens] == ["x", "y", "z"]
    assert pretty(r.expr) == "x (z y)"


def test_magic_statement():
    stmts = parse_cell("%trace K x y")
    assert len(stmts) == 1
    m = stmts[0]
    assert isinstance(m, Magic)
    assert m.name == "%trace"
    assert len(m.arg_tokens) == 3


def test_unbalanced_parens_is_parse_error():
    with pytest.raises(ParseError):
        parse_cell("K (x y")


def test_unmatched_close_paren_is_parse_error():
    with pytest.raises(ParseError):
        parse_cell("K x) y")


def test_parse_error_has_line_col_caret():
    try:
        parse_cell("K x)")
    except ParseError as e:
        assert e.line_no == 0
        assert "^" in e.format()
    else:
        pytest.fail("expected ParseError")


def test_continuation_line_joining():
    stmts = parse_cell("K (x\ny)")
    assert len(stmts) == 1
    assert pretty(stmts[0].expr) == "K (x y)"


def test_is_incomplete_unclosed_paren():
    assert is_incomplete("B (S")
    assert not is_incomplete("B (S K)")
    assert paren_balance("B (S") == 1
    assert paren_balance("K x y") == 0


# --- name canonicalization (§4.3) -----------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("Q₁", "Q1"),
    ("B₂", "B2"),
    ("W′", "W'"),
    ("W¹", "W'"),
    ("C*", "C*"),
    ("C**", "C**"),
    ("foo_bar", "foo_bar"),
])
def test_canonicalize(raw, expected):
    assert canonicalize(raw) == expected
