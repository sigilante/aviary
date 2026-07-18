"""Bird-registry test fixtures/oracles, hand-verified against the two
source URLs named in SPEC.md §1/§5.5:

  * Wolfram Data Repository, "Combinator Birds":
    https://datarepository.wolframcloud.com/resources/Combinator-Birds/
    -- as of this writing the dataset's actual rows are rendered as
    *images* on that page (not machine-extractable text), and the page
    itself names its primary source as Chris Rathman's "Combinator
    Birds" chart. We fetched that chart directly (via the Wayback
    Machine, since the live angelfire.com domain no longer resolves):
    https://web.archive.org/web/2023/https://www.angelfire.com/tx4/cus/combinator/birds.html
    Every rule below was extracted programmatically from that chart's
    HTML table (see scripts in the implementer's scratch area) and
    cross-checked column by column against SPEC.md's own §5.2 table.
  * combinatorylogic.com table: https://combinatorylogic.com/table.html
    (a smaller, ~24-entry table; used below as a second, independent
    oracle for the birds it covers).

RATHMAN_RULE: canonical bird name -> that bird's reduction rule RHS, in
Aviary surface syntax, transcribed from Rathman's "Function Abstraction"
column. Used by test_birds.py to assert every registry rule matches this
independently-sourced rule *exactly* (SPEC.md §12 item 2). `Y`, `Φ`
(Phoenix) and `Ψ` (Psi) are absent from this dict: Phoenix/Psi simply
aren't in Rathman's chart (they came from combinatorylogic.com instead,
see CL note in test_birds.py), and Y's row in Rathman's raw HTML uses a
"symbol font" character-mapping trick for its self-reference that our
plain-text extraction can't recover cleanly (Y is independently verified
elsewhere via its explicit `ski` override, checked against Curry's
published standard form for the Sage Bird).

TWO SOURCE DISCREPANCIES were found and corrected here (not silently --
noted so a human reviewer can double-check the reasoning):

1. Rathman's own "Function Abstraction" column for V* (Vireo Once
   Removed) reads `abcd.acbd` (i.e. "a c b d"), disagreeing with
   SPEC.md's `V* a b c d = a d b c`. We do NOT use the literal column
   value here because it is self-contradictory with the *rest of
   Rathman's own chart*: Rathman's "Combinator" column defines
   `V* = C*F*`, and unfolding that formula using Rathman's own
   (internally consistent) C* and F* rows gives `a d b c`, not
   `a c b d`. Independently, Rathman's own V** row (`BV*` = `a b e c d`)
   is only consistent with V* = `a d b c` (unfolding
   `(B V*) a b c d e = V* (a b) c d e`, which needs V* to map
   `p q r s -> p s q r`, i.e. `a d b c`, to yield `a b e c d`). So the
   lambda-column entry for V* is a plain transcription typo in the
   source; we record the value implied by the rest of the source
   (which matches SPEC.md).

2. Rathman's "SK Combinator" (fully-expanded S/K) column has *the exact
   same string* for B2 (Bunting, arity 5) and B3 (Becard, arity 4) --
   confirmed by inspecting the raw HTML row-by-row, not just our own
   extraction. Applying that shared string to 5 fresh variables matches
   B2 behaviorally; applying it to 4 fresh variables (B3's arity) leaves
   a redex un-consumed, i.e. it is not B3's real SK form -- it's a
   copy/paste duplicate of B2's row. We omit a `RATHMAN_SK` entry for
   B3 rather than assert against a value we know the source got wrong
   for that row. (Rathman's separate, coarser "Combinator" column does
   correctly distinguish them: `B(BBB)B` for B2 vs `B(BB)B` for B3.)

RATHMAN_SK: canonical bird name -> a fully-expanded S/K (Curry-basis)
term, transcribed from Rathman's "SK Combinator" column. Used as a
behavioral oracle (SPEC.md §12 item 3): `bird x1..xn` and
`oracle x1..xn` must reduce to the same normal form, even though the
derived S/K/I form our own bracket-abstraction produces will generally
differ syntactically.

CL_ORACLE: canonical bird name -> a term (over other registry birds,
not necessarily pure SKI) transcribed from combinatorylogic.com's "CR1"
column, covering the subset of birds that table lists. Also used as a
behavioral oracle for §12 item 3, independent of RATHMAN_SK.
"""

RATHMAN_RULE: dict[str, str] = {
    'B': 'a (b c)',
    'B1': 'a (b c d)',
    'B2': 'a (b c d e)',
    'B3': 'a (b (c d))',
    'C': 'a c b',
    'C*': 'a b d c',
    'C**': 'a b c e d',
    'D': 'a b (c d)',
    'D1': 'a b c (d e)',
    'D2': 'a (b c) (d e)',
    'E': 'a b (c d e)',
    'F': 'c b a',
    'F*': 'a d c b',
    'F**': 'a b e d c',
    'G': 'a d (b c)',
    'H': 'a b c b',
    'I': 'a',
    'I*': 'a b',
    'I**': 'a b c',
    'J': 'a b (a d c)',
    'K': 'a',
    'KM': 'b b',
    "KM'": 'a a',
    'Ki': 'b',
    'L': 'a (b b)',
    'M': 'a a',
    'M2': 'a b (a b)',
    'O': 'b (a b)',
    'Q': 'b (a c)',
    'Q1': 'a (c b)',
    'Q2': 'b (c a)',
    'Q3': 'c (a b)',
    'Q4': 'c (b a)',
    'R': 'b c a',
    'R*': 'a c d b',
    'R**': 'a b d e c',
    'S': 'a c (b c)',
    'T': 'b a',
    'U': 'b (a a b)',
    'V': 'c a b',
    'V*': 'a d b c',  # corrected; see module docstring, discrepancy 1
    'V**': 'a b e c d',
    'W': 'a b b',
    "W'": 'b a a',
    'W*': 'a b c c',
    'W**': 'a b c d d',
    'Ê': 'a (b c d) (e f g)',
}

RATHMAN_SK: dict[str, str] = {
    'B': '((S(K S))K)',
    'B1': '((S(K((S(K S))K)))((S(K S))K))',
    'B2': '((S(K((S(K((S(K S))K)))((S(K S))K))))((S(K S))K))',
    # 'B3' intentionally omitted -- source bug, see module docstring, discrepancy 2
    'C': '((S((S(K((S(K S))K)))S))(K K))',
    'C*': '(S(K((S((S(K((S(K S))K)))S))(K K))))',
    'C**': '(S(K(S(K((S((S(K((S(K S))K)))S))(K K))))))',
    'D': '(S(K((S(K S))K)))',
    'D1': '(S(K(S(K((S(K S))K)))))',
    'D2': '((S(K((S(K S))K)))(S(K((S(K S))K))))',
    'E': '(S(K((S(K((S(K S))K)))((S(K S))K))))',
    'F': '((S(K((S((S K)K))(K((S(K(S((S K)K))))K)))))((S(K((S(K((S(K S))K)))((S(K S))K))))((S(K(S((S K)K))))K)))',
    'F*': '((S(K(S(K((S((S(K((S(K S))K)))S))(K K))))))((S(K((S((S(K((S(K S))K)))S))(K K))))(S(K((S((S(K((S(K S))K)))S))(K K))))))',
    'F**': '(S(K((S(K(S(K((S((S(K((S(K S))K)))S))(K K))))))((S(K((S((S(K((S(K S))K)))S))(K K))))(S(K((S((S(K((S(K S))K)))S))(K K))))))))',
    'G': '((S(K((S(K S))K)))((S((S(K((S(K S))K)))S))(K K)))',
    'H': '((S(K((S(K(S((S(K((S((S K)K))((S K)K))))((S(K((S(K S))K)))((S(K(S((S K)K))))K))))))K)))(S(K((S((S(K((S(K S))K)))S))(K K)))))',
    'I': '((S K)K)',
    'I*': '(S(S K))',
    'J': '((S(K(S(K((S((S(K((S(K S))K)))S))(K K))))))((S((S(K((S((S K)K))((S K)K))))((S(K((S(K S))K)))((S(K(S((S K)K))))K))))(K((S(K((S((S(K((S(K S))K)))S))(K K))))(S(K((S(K((S(K S))K)))((S(K S))K))))))))',
    'K': 'K',
    'KM': '(K((S((S K)K))((S K)K)))',
    "KM'": '((S(K(S(K((S((S K)K))((S K)K))))))K)',
    'Ki': '(K((S K)K))',
    'L': '((S((S(K S))K))(K((S((S K)K))((S K)K))))',
    'M': '((S((S K)K))((S K)K))',
    'M2': '(S(K((S((S K)K))((S K)K))))',
    'O': '(S((S K)K))',
    'Q': '((S(K(S((S(K S))K))))K)',
    'Q1': '((S(K((S((S(K((S(K S))K)))S))(K K))))((S(K S))K))',
    'Q2': '((S(K(S((S(K((S((S(K((S(K S))K)))S))(K K))))((S(K S))K)))))K)',
    'Q3': '(S(K((S(K(S((S K)K))))K)))',
    'Q4': '((S(K((S((S(K((S(K S))K)))S))(K K))))((S(K(S((S(K((S((S(K((S(K S))K)))S))(K K))))((S(K S))K)))))K))',
    'R': '((S(K((S(K S))K)))((S(K(S((S K)K))))K))',
    'R*': '((S(K((S((S(K((S(K S))K)))S))(K K))))(S(K((S((S(K((S(K S))K)))S))(K K)))))',
    'R**': '(S(K((S(K((S((S(K((S(K S))K)))S))(K K))))(S(K((S((S(K((S(K S))K)))S))(K K)))))))',
    'S': 'S',
    'T': '((S(K(S((S K)K))))K)',
    'U': '((S(K(S((S K)K))))((S((S K)K))((S K)K)))',
    'V': '((S(K((S((S(K((S(K S))K)))S))(K K))))((S(K(S((S K)K))))K))',
    'V*': '((S(K((S((S(K((S(K S))K)))S))(K K))))((S(K(S(K((S((S(K((S(K S))K)))S))(K K))))))((S(K((S((S(K((S(K S))K)))S))(K K))))(S(K((S((S(K((S(K S))K)))S))(K K)))))))',
    'V**': '(S(K((S(K((S((S(K((S(K S))K)))S))(K K))))((S(K(S(K((S((S(K((S(K S))K)))S))(K K))))))((S(K((S((S(K((S(K S))K)))S))(K K))))(S(K((S((S(K((S(K S))K)))S))(K K)))))))))',
    'W': '((S(K(S((S(K((S((S K)K))((S K)K))))((S(K((S(K S))K)))((S(K(S((S K)K))))K))))))K)',
    "W'": '((S(K(S((S(K(S((S(K((S((S K)K))((S K)K))))((S(K((S(K S))K)))((S(K(S((S K)K))))K))))))K))))K)',
    'W*': '(S(K((S(K(S((S(K((S((S K)K))((S K)K))))((S(K((S(K S))K)))((S(K(S((S K)K))))K))))))K)))',
    'W**': '(S(K(S(K((S(K(S((S(K((S((S K)K))((S K)K))))((S(K((S(K S))K)))((S(K(S((S K)K))))K))))))K)))))',
    'Ê': '((S(K((S(K((S(K S))K)))((S(K S))K))))(S(K((S(K((S(K S))K)))((S(K S))K)))))',
}

CL_ORACLE: dict[str, str] = {
    "I": "S K K",
    "K": "K",
    "Ki": "K I",
    "W": "C (B M R)",
    "C": "S (B B S) (K K)",
    "B": "S (K S) K",
    "B1": "B B B",
    "B2": "B (B B B) B",
    "B3": "B (B B) B",
    "S": "S",
    "D": "B B",
    "D1": "B (B B)",
    "D2": "B B (B B)",
    "E": "B (B B B)",
    "Ê": "B (B B B) (B (B B B))",
}
