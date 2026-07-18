"""Lexer + parser for Aviary's surface syntax (SPEC.md §4).

Grammar:

    stmt   := magic | alias | rule | expr
    alias  := NAME ':=' expr
    rule   := NAME VAR+ '->' expr
    expr   := term+                      # application, left-associative
    term   := '(' expr ')' | ATOM

Lexing: delimiters are whitespace, '(', ')', and the reserved operators
':=' '->' '#'. A token is any maximal run of other characters -- no
single-letter special-casing.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from .terms import Atom, App, Term

# --- Name canonicalization (SPEC.md §4.3) ----------------------------------

_SUBSCRIPT_DIGITS = {
    "₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
    "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9",
}
_PRIME = "′"  # ′
_SUPERSCRIPT_ONE = "¹"  # ¹


def canonicalize(token: str) -> str:
    """Apply the four canonicalization steps of §4.3 to a single token."""
    s = unicodedata.normalize("NFC", token)
    out = []
    for ch in s:
        if ch in _SUBSCRIPT_DIGITS:
            out.append(_SUBSCRIPT_DIGITS[ch])
        elif ch == _PRIME:
            out.append("'")
        elif ch == _SUPERSCRIPT_ONE:
            out.append("'")
        else:
            out.append(ch)
    return "".join(out)


# --- Errors -----------------------------------------------------------------


class ParseError(Exception):
    def __init__(self, message: str, line_text: str, line_no: int, col: int):
        self.message = message
        self.line_text = line_text
        self.line_no = line_no
        self.col = col
        super().__init__(self.format())

    def format(self) -> str:
        caret = " " * self.col + "^"
        return (
            f"ParseError: {self.message} (line {self.line_no}, col {self.col + 1})\n"
            f"    {self.line_text}\n"
            f"    {caret}"
        )


# --- Tokenizing ---------------------------------------------------------------


@dataclass(frozen=True)
class Token:
    text: str          # raw token text, as it appeared in source
    canonical: str      # canonicalized name (only meaningful for ATOM kind)
    kind: str           # 'atom' | '(' | ')' | ':=' | '->'
    line: int           # 0-based physical line index within the cell
    col: int             # 0-based column offset within that physical line
    line_text: str      # the full physical line text (for error captions)


def tokenize_line(text: str, line_no: int) -> list[Token]:
    """Tokenize one physical line. Comments (# to EOL) are dropped."""
    tokens: list[Token] = []
    pos = 0
    n = len(text)
    while pos < n:
        c = text[pos]
        if c in " \t\r":
            pos += 1
            continue
        if c == "#":
            break
        if c == "(":
            tokens.append(Token("(", "(", "(", line_no, pos, text))
            pos += 1
            continue
        if c == ")":
            tokens.append(Token(")", ")", ")", line_no, pos, text))
            pos += 1
            continue
        if text[pos:pos + 2] == ":=":
            tokens.append(Token(":=", ":=", ":=", line_no, pos, text))
            pos += 2
            continue
        if text[pos:pos + 2] == "->":
            tokens.append(Token("->", "->", "->", line_no, pos, text))
            pos += 2
            continue
        start = pos
        while pos < n:
            ch = text[pos]
            if ch in " \t\r" or ch in "()":
                break
            if ch == "#":
                break
            if text[pos:pos + 2] == ":=" or text[pos:pos + 2] == "->":
                break
            pos += 1
        raw = text[start:pos]
        tokens.append(Token(raw, canonicalize(raw), "atom", line_no, start, text))
    return tokens


def _paren_delta(text: str) -> int:
    """Net paren balance of a line, ignoring the comment tail."""
    code = text.split("#", 1)[0]
    return code.count("(") - code.count(")")


def _is_blank(text: str) -> bool:
    return text.split("#", 1)[0].strip() == ""


@dataclass
class LogicalLine:
    """A statement's worth of tokens, possibly spanning several physical
    lines joined because of unclosed parens."""
    tokens: list[Token]
    start_line: int
    raw_lines: list[str]
    balance: int  # final paren balance; 0 if well-formed


def split_statements(cell_text: str) -> list[LogicalLine]:
    """Split a cell into logical (possibly multi-physical-line) statements,
    joining continuation lines the way an unclosed-paren console prompt
    would (SPEC.md §4.2)."""
    lines = cell_text.split("\n")
    groups: list[LogicalLine] = []
    i = 0
    n = len(lines)
    while i < n:
        if _is_blank(lines[i]):
            i += 1
            continue
        start_line = i
        raw_lines = [lines[i]]
        balance = _paren_delta(lines[i])
        while balance > 0 and i + 1 < n:
            i += 1
            raw_lines.append(lines[i])
            balance += _paren_delta(lines[i])
        tokens: list[Token] = []
        for offset, raw in enumerate(raw_lines):
            tokens.extend(tokenize_line(raw, start_line + offset))
        groups.append(LogicalLine(tokens=tokens, start_line=start_line,
                                   raw_lines=raw_lines, balance=balance))
        i += 1
    return groups


def is_incomplete(line_text: str) -> bool:
    """True iff a single line (as typed so far at a console) has unclosed
    parens (SPEC.md §4.2, §10 do_is_complete)."""
    return _paren_delta(line_text) > 0


def paren_balance(code: str) -> int:
    """Net paren balance across every line of ``code`` (comments excluded).
    Positive means unclosed parens remain open (SPEC.md §10 do_is_complete)."""
    return sum(_paren_delta(line) for line in code.split("\n"))


# --- Statement AST ------------------------------------------------------------


@dataclass
class Magic:
    name: str
    arg_tokens: list[Token]
    line: LogicalLine


@dataclass
class Alias:
    name_token: Token
    expr: Term
    line: LogicalLine


@dataclass
class Rule:
    name_token: Token
    var_tokens: list[Token]
    expr: Term
    line: LogicalLine


@dataclass
class Expr:
    expr: Term
    line: LogicalLine


Stmt = Magic | Alias | Rule | Expr


def _find_top_level(tokens: list[Token], kinds: tuple[str, ...]) -> Optional[int]:
    """Index of the first token at paren-depth 0 whose kind is in ``kinds``."""
    depth = 0
    for i, t in enumerate(tokens):
        if t.kind == "(":
            depth += 1
        elif t.kind == ")":
            depth -= 1
        elif depth == 0 and t.kind in kinds:
            return i
    return None


def _err_at(token: Token, message: str) -> ParseError:
    return ParseError(message, token.line_text, token.line, token.col)


def _parse_expr_tokens(tokens: list[Token], line: LogicalLine) -> Term:
    if not tokens:
        # Should not happen for well-formed statements; caller guards.
        raise ParseError("expected an expression", line.raw_lines[0] if line.raw_lines else "", line.start_line, 0)
    pos = 0

    def parse_term() -> Term:
        nonlocal pos
        if pos >= len(tokens):
            last = tokens[-1]
            raise _err_at(last, "unexpected end of expression")
        t = tokens[pos]
        if t.kind == "(":
            pos += 1
            inner = parse_expr()
            if pos >= len(tokens) or tokens[pos].kind != ")":
                raise _err_at(t, "unmatched '('")
            pos += 1
            return inner
        if t.kind == ")":
            raise _err_at(t, "unexpected ')'")
        if t.kind in (":=", "->"):
            raise _err_at(t, f"unexpected '{t.kind}'")
        pos += 1
        return Atom(t.canonical)

    def parse_expr() -> Term:
        nonlocal pos
        first = parse_term()
        result = first
        while pos < len(tokens) and tokens[pos].kind not in (")",):
            nxt = tokens[pos]
            if nxt.kind in (":=", "->"):
                raise _err_at(nxt, f"unexpected '{nxt.kind}' inside expression")
            result = App(result, parse_term())
        return result

    term = parse_expr()
    if pos != len(tokens):
        raise _err_at(tokens[pos], "unexpected token")
    return term


def parse_statement(line: LogicalLine) -> Stmt:
    tokens = line.tokens
    if line.balance != 0:
        # Unbalanced across the (possibly joined) line group.
        bad = tokens[-1] if tokens else None
        text = line.raw_lines[-1] if line.raw_lines else ""
        ln = line.start_line + len(line.raw_lines) - 1
        col = len(text.rstrip())
        raise ParseError("unbalanced parentheses", text, ln, max(col, 0))
    if not tokens:
        raise ParseError("empty statement", line.raw_lines[0] if line.raw_lines else "", line.start_line, 0)

    first = tokens[0]
    if first.kind == "atom" and first.text.startswith("%"):
        return Magic(name=first.canonical, arg_tokens=tokens[1:], line=line)

    alias_idx = _find_top_level(tokens, (":=",))
    arrow_idx = _find_top_level(tokens, ("->",))

    if alias_idx is not None and (arrow_idx is None or alias_idx < arrow_idx):
        lhs = tokens[:alias_idx]
        rhs = tokens[alias_idx + 1:]
        if len(lhs) != 1 or lhs[0].kind != "atom":
            bad = lhs[0] if lhs else tokens[alias_idx]
            raise _err_at(bad, "alias left-hand side must be a single name")
        if not rhs:
            raise _err_at(tokens[alias_idx], "alias has no body")
        expr = _parse_expr_tokens(rhs, line)
        return Alias(name_token=lhs[0], expr=expr, line=line)

    if arrow_idx is not None:
        lhs = tokens[:arrow_idx]
        rhs = tokens[arrow_idx + 1:]
        if len(lhs) < 2 or any(t.kind != "atom" for t in lhs):
            raise _err_at(tokens[0], "rule left-hand side must be NAME VAR+")
        if not rhs:
            raise _err_at(tokens[arrow_idx], "rule has no body")
        expr = _parse_expr_tokens(rhs, line)
        return Rule(name_token=lhs[0], var_tokens=lhs[1:], expr=expr, line=line)

    expr = _parse_expr_tokens(tokens, line)
    return Expr(expr=expr, line=line)


def parse_expr_tokens(tokens: list[Token], line: LogicalLine) -> Term:
    """Public wrapper: parse a bare token list as an expression."""
    return _parse_expr_tokens(tokens, line)


def parse_cell(cell_text: str) -> list[Stmt]:
    """Parse a full cell into a list of statements."""
    return [parse_statement(line) for line in split_statements(cell_text)]
