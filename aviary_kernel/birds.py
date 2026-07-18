"""The bird registry (SPEC.md §5).

Verification (§5.5, done by the implementer against the two source URLs):

  * Wolfram Data Repository, "Combinator Birds":
    https://datarepository.wolframcloud.com/resources/Combinator-Birds/
    (data rendered as images on that page; not machine-extractable, so as
    a verification proxy we used Chris Rathman's "Combinator Birds" chart
    -- https://www.angelfire.com/tx4/cus/combinator/birds.html (fetched via
    the Wayback Machine, https://web.archive.org/web/2023/<url>) -- which
    both the SPEC and the Wolfram page itself cite as their common primary
    source, and which gives an independent, fully-expanded SK form for
    every entry (usable as an oracle, see tests/test_birds.py).
  * combinatorylogic.com table: https://combinatorylogic.com/table.html
    (covers a smaller ~24-entry subset: B, B1-B3, C, D, D1-D2, E, Ê, S,
    Phi, Psi, I, K, kite, W, plus a few extras with no Smullyan name).

Every row of SPEC.md's §5.2 table was cross-checked against both sources
and confirmed correct, INCLUDING the once/twice-removed permuting birds
(C*, C**, F*, F**, R*, R**, V*, V**) and the Jay -- the classic
transcription-error spots the spec calls out. No correction to the SPEC
table was needed anywhere; three transcription bugs turned up in the
*source* material itself while building the test fixtures (see the
header of tests/fixtures_birds.py for the full reasoning):

  1. Rathman's own "Function Abstraction" column for V* is misprinted as
     `abcd.acbd` -- but Rathman's own "Combinator" formula for V*
     (`C*F*`) evaluates, by unfolding Rathman's own C* and F* rows, to
     `a d b c`, matching both SPEC.md and an independent cross-check
     against Rathman's own V** row. Internal typo in that one column.
  2. Rathman's fully-expanded "SK Combinator" column is byte-identical
     for B2 and B3 (arities 5 and 4 respectively) -- a copy/paste
     duplicate, confirmed in the raw HTML.
  3. Rathman's row for Y reuses the same Symbol-font "l -> λ" HTML
     entity for both the rule's outer binder and its inner
     self-reference (which should read "Y"), i.e. a copy/paste slip
     rather than a different encoding.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import Token, tokenize_line, LogicalLine, _parse_expr_tokens
from .terms import Atom, App, Term

_FORMALS = "abcdefg"  # matches the max arity in the table (7, Bald Eagle)


def _r(src: str) -> Term:
    """Parse a bare rule-RHS expression string, e.g. 'a (b c)'."""
    line = LogicalLine(tokens=[], start_line=0, raw_lines=[src], balance=0)
    tokens = tokenize_line(src, 0)
    return _parse_expr_tokens(tokens, line)


@dataclass(frozen=True)
class Bird:
    name: str                 # canonical name, e.g. "Q1"
    display: str               # preferred Unicode display, e.g. "Q₁"
    aliases: tuple[str, ...]   # additional canonical lookup keys
    bird_name: str             # "Quixotic Bird"
    arity: int
    rule: Term                 # RHS over formal vars a, b, c, ... (Atom nodes)
    ski: Term | None = None    # explicit override; None => derive via abstraction.py

    @property
    def formals(self) -> tuple[str, ...]:
        return tuple(_FORMALS[: self.arity])


def _bird(name, display, aliases, bird_name, arity, rule_src, ski_src=None) -> Bird:
    ski = _r(ski_src) if ski_src is not None else None
    return Bird(name, display, tuple(aliases), bird_name, arity, _r(rule_src), ski)


# Curry's standard SKI form for Y, per SPEC.md §5.2:
#   S (K (S I I)) (S (S (K S) K) (K (S I I)))
_Y_SKI = "S (K (S I I)) (S (S (K S) K) (K (S I I)))"

BIRDS: tuple[Bird, ...] = (
    _bird("B", "B", [], "Bluebird", 3, "a (b c)"),
    _bird("B1", "B₁", [], "Blackbird", 4, "a (b c d)"),
    _bird("B2", "B₂", [], "Bunting", 5, "a (b c d e)"),
    _bird("B3", "B₃", [], "Becard", 4, "a (b (c d))"),
    _bird("C", "C", [], "Cardinal", 3, "a c b"),
    _bird("C*", "C*", [], "Cardinal Once Removed", 4, "a b d c"),
    _bird("C**", "C**", [], "Cardinal Twice Removed", 5, "a b c e d"),
    _bird("D", "D", [], "Dove", 4, "a b (c d)"),
    _bird("D1", "D₁", [], "Dickcissel", 5, "a b c (d e)"),
    _bird("D2", "D₂", [], "Dovekie", 5, "a (b c) (d e)"),
    _bird("E", "E", [], "Eagle", 5, "a b (c d e)"),
    _bird("Ê", "Ê", ["E^"], "Bald Eagle", 7, "a (b c d) (e f g)"),
    _bird("F", "F", [], "Finch", 3, "c b a"),
    _bird("F*", "F*", [], "Finch Once Removed", 4, "a d c b"),
    _bird("F**", "F**", [], "Finch Twice Removed", 5, "a b e d c"),
    _bird("G", "G", [], "Goldfinch", 4, "a d (b c)"),
    _bird("H", "H", [], "Hummingbird", 3, "a b c b"),
    _bird("I", "I", [], "Identity (Idiot)", 1, "a"),
    _bird("I*", "I*", [], "Identity Once Removed", 2, "a b"),
    _bird("I**", "I**", [], "Identity Twice Removed", 3, "a b c"),
    _bird("J", "J", [], "Jay", 4, "a b (a d c)"),
    _bird("K", "K", [], "Kestrel", 2, "a"),
    _bird("Ki", "Ki", [], "Kite", 2, "b"),
    _bird("KM", "KM", [], "Konstant Mocker", 2, "b b"),
    _bird("KM'", "KM'", [], "Crossed Konstant Mocker", 2, "a a"),
    _bird("L", "L", [], "Lark", 2, "a (b b)"),
    _bird("M", "M", [], "Mockingbird", 1, "a a"),
    _bird("M2", "M₂", [], "Double Mockingbird", 2, "a b (a b)"),
    _bird("O", "O", [], "Owl", 2, "b (a b)"),
    _bird("Φ", "Φ", ["Phi"], "Phoenix", 4, "a (b d) (c d)"),
    _bird("Ψ", "Ψ", ["Psi"], "Psi Bird", 4, "a (b c) (b d)"),
    _bird("Q", "Q", [], "Queer Bird", 3, "b (a c)"),
    _bird("Q1", "Q₁", [], "Quixotic Bird", 3, "a (c b)"),
    _bird("Q2", "Q₂", [], "Quizzical Bird", 3, "b (c a)"),
    _bird("Q3", "Q₃", [], "Quirky Bird", 3, "c (a b)"),
    _bird("Q4", "Q₄", [], "Quacky Bird", 3, "c (b a)"),
    _bird("R", "R", [], "Robin", 3, "b c a"),
    _bird("R*", "R*", [], "Robin Once Removed", 4, "a c d b"),
    _bird("R**", "R**", [], "Robin Twice Removed", 5, "a b d e c"),
    _bird("S", "S", [], "Starling", 3, "a c (b c)"),
    _bird("T", "T", [], "Thrush", 2, "b a"),
    _bird("U", "U", [], "Turing Bird", 2, "b (a a b)"),
    _bird("V", "V", [], "Vireo", 3, "c a b"),
    _bird("V*", "V*", [], "Vireo Once Removed", 4, "a d b c"),
    _bird("V**", "V**", [], "Vireo Twice Removed", 5, "a b e c d"),
    _bird("W", "W", [], "Warbler", 2, "a b b"),
    _bird("W*", "W*", [], "Warbler Once Removed", 3, "a b c c"),
    _bird("W**", "W**", [], "Warbler Twice Removed", 4, "a b c d d"),
    _bird("W'", "W'", [], "Converse Warbler", 2, "b a a"),
    _bird("Y", "Y", [], "Sage Bird", 1, "a (Y a)", ski_src=_Y_SKI),
)

# --- Lookup tables ----------------------------------------------------------

BY_NAME: dict[str, Bird] = {}
for _b in BIRDS:
    BY_NAME[_b.name] = _b
    for _a in _b.aliases:
        BY_NAME[_a] = _b

# Theta: preloaded exactly as if the user had typed `Θ := U U` (§5.2).
# It is not a Bird (no arity/rule template of its own -- it's an alias),
# but it is protected from redefinition/undef like a built-in. See
# kernel.py / environment.py where BUILTIN_ALIASES is installed at
# session start.
BUILTIN_ALIASES: dict[str, tuple[str, Term]] = {
    "Θ": ("Θ", App(Atom("U"), Atom("U"))),
}
BUILTIN_ALIAS_KEYS: dict[str, str] = {"Θ": "Θ", "Theta": "Θ"}


def lookup_bird(name: str) -> Bird | None:
    return BY_NAME.get(name)
