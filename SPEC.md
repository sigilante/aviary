# Aviary — a combinator-calculus Jupyter kernel

**Status:** specification, ready for implementation.
**Substrate:** Python ≥ 3.10, `ipykernel`.
**Evaluation:** normal-order (leftmost-outermost, lazy) reduction to full normal form.
**Vocabulary:** S/K/I, BCKW, and the Smullyan aviary; arbitrary Unicode atoms as free variables; user-defined combinators.

---

## 1. Overview

Aviary is a Jupyter kernel that evaluates combinatory-logic expressions. A cell
like

```
K ▲ (M M)
```

reduces under normal order and prints

```
▲        [1 step]
```

(note: `M M` is never reduced — this is the laziness litmus test; see §12).

Core capabilities:

1. Parse applicative expressions over a large built-in bird registry plus
   arbitrary user symbols (`▲`, `🟢`, `foo`, …) treated as inert free variables.
2. Reduce with normal-order strategy, fuel-bounded, with optional step trace.
3. Expand any expression to the pure **S/K/I** basis (or strict **S/K**) via
   bracket abstraction.
4. Let users define new combinators in-session, by alias or by rewrite rule,
   which then reduce and basis-expand exactly like built-ins.

Bird data sources (used for the registry and as test oracles):

- Wolfram Data Repository, *Combinator Birds* (~50 entries: symbol, rule,
  arity, SK-basis form): https://datarepository.wolframcloud.com/resources/Combinator-Birds/
- combinatorylogic.com table (λ-calculus and SKI forms, 29 entries):
  https://combinatorylogic.com/table.html
- Both derive from Smullyan, *To Mock a Mockingbird*, and Chris Rathman's
  "Combinator Birds" chart.

We use the letter/subscript names (`Q1`/`Q₁`), **not** Wolfram's three-letter
names (`dov`, `moc`, …).

---

## 2. Package layout

```
aviary/
  pyproject.toml            # package name: aviary-kernel
  aviary_kernel/
    __init__.py
    kernel.py               # AviaryKernel(ipykernel.kernelbase.Kernel)
    parser.py               # lexer + parser → Term
    terms.py                # Term model, pretty-printer
    birds.py                # registry data (see §5)
    reduce.py               # normal-order reducer, tracing, fuel
    abstraction.py          # bracket abstraction → S/K/I and S/K
    magics.py               # %-command dispatch
    install.py              # `python -m aviary_kernel.install` writes kernelspec
    kernelspec/kernel.json  # display_name "Aviary (Combinator Calculus)", language "combinatory-logic"
  tests/
    test_parser.py test_reduce.py test_birds.py test_abstraction.py test_kernel.py
  SPEC.md
  README.md
```

Install path: `pip install -e . && python -m aviary_kernel.install [--user]`.
`test_kernel.py` should use `jupyter_kernel_test` or drive the kernel via
`jupyter_client.BlockingKernelClient` for end-to-end execute-request tests.

---

## 3. Term model (`terms.py`)

Binary application trees over atoms:

```python
Term = Atom | App
Atom(name: str)                 # canonical name (see §4.3); combinator or free variable
App(fn: Term, arg: Term)
```

- Atoms are interned by canonical name; whether an atom is a combinator is
  determined at reduction time by lookup in (built-ins ∪ session definitions),
  so a symbol defined *after* a term is entered still takes effect.
- Pretty-printing: application is left-associative and implicit; parenthesize
  only right-nested applications. `App(App(S, K), App(K, I))` → `S K (K I)`.
  Tokens are space-separated on output.
- Display names use the session's preferred script (Unicode subscripts by
  default, ASCII under `%ascii on`): `Q₁` vs `Q1`.

---

## 4. Surface syntax (`parser.py`)

### 4.1 Cell structure

- A cell is a sequence of **lines**; each non-empty line is one statement.
- `#` begins a comment to end of line.
- A statement is a **magic** (first token starts with `%`), a **definition**
  (contains `:=` or `->` at top level), or an **expression**.
- The cell's `execute_result` is the value of the **last** expression
  statement; earlier expressions print their results via `stream`/
  `display_data` as they are evaluated. Definitions print a one-line
  confirmation.

### 4.2 Grammar

```
stmt   := magic | alias | rule | expr
alias  := NAME ':=' expr
rule   := NAME VAR+ '->' expr
expr   := term+                      # application, left-associative
term   := '(' expr ')' | ATOM
```

**Lexing.** Delimiters are whitespace, `(`, `)`, and the reserved operators
`:=` `->` `#`. A token is any maximal run of other characters. Consequences:

- Application requires whitespace or parens between atoms: `S K K` is three
  atoms; `SKK` is a single (free-variable) atom named `SKK`. This is the price
  of arbitrary multi-character and Unicode names (`B1`, `Q₁`, `W'`, `▲🟢`),
  and it must hold uniformly — do **not** special-case single letters.
- Any non-delimiter Unicode is a valid atom: `▲`, `🟢`, `λx` (one token),
  `foo_bar`. Emoji ZWJ sequences work automatically since tokens are
  character runs, not single codepoints.
- `(` `)` never appear inside tokens.

Parse errors report line, column, and a caret under the offending token.
Unbalanced parens across a line are an error (each line is self-contained).
`do_is_complete` (§10) returns `incomplete` for a line with unclosed parens so
the console prompts for continuation; the parser then joins continued lines.

### 4.3 Name canonicalization

Applied to every token at lex time:

1. Unicode NFC normalization.
2. Subscript digits U+2080–U+2089 → ASCII digits (`Q₁` ≡ `Q1`, `B₂` ≡ `B2`).
3. Prime U+2032 `′` → ASCII apostrophe `'` (`W′` ≡ `W'`).
4. Superscript one U+00B9 `¹` → `'` (some tables print Converse Warbler `W¹`).

The canonical name is the post-normalization form; display re-applies the
session script preference (subscripts on by default) **only for registry
names**, never for free variables. `*` and `'` are ordinary name characters
(`C*`, `C**`, `W'`). `Ê` (Bald Eagle) additionally has the ASCII alias `E^`.

---

## 5. Bird registry (`birds.py`)

### 5.1 Data model

```python
@dataclass(frozen=True)
class Bird:
    name: str                # canonical ASCII name, e.g. "Q1"
    display: str             # preferred Unicode, e.g. "Q₁"
    aliases: tuple[str, ...] # e.g. ("E^",) for Ê
    bird_name: str           # "Quixotic Bird"
    arity: int
    rule: Term               # RHS over formal vars a, b, c, … (Var atoms)
    ski: Term | None         # explicit override; None ⇒ derive via §8
```

`ski` is stored **only** for self-referential birds (Y, U’s friends if any);
for everything else the S/K/I form is *derived* from `rule` by bracket
abstraction. Never hand-copy SKI strings for derivable birds — the published
SKI columns are **test vectors** (§12), not data. This also guarantees
user-defined combinators expand by exactly the same mechanism.

### 5.2 The aviary

The registry below is the standard Smullyan/Rathman set (the Wolfram dataset's
contents). Rules are written λ-style; `X a b … = rhs` means arity = number of
LHS vars.

| Name | Bird | Rule |
|---|---|---|
| `B` | Bluebird | `B a b c = a (b c)` |
| `B1`/`B₁` | Blackbird | `B₁ a b c d = a (b c d)` |
| `B2`/`B₂` | Bunting | `B₂ a b c d e = a (b c d e)` |
| `B3`/`B₃` | Becard | `B₃ a b c d = a (b (c d))` |
| `C` | Cardinal | `C a b c = a c b` |
| `C*` | Cardinal Once Removed | `C* a b c d = a b d c` |
| `C**` | Cardinal Twice Removed | `C** a b c d e = a b c e d` |
| `D` | Dove | `D a b c d = a b (c d)` |
| `D1`/`D₁` | Dickcissel | `D₁ a b c d e = a b c (d e)` |
| `D2`/`D₂` | Dovekie | `D₂ a b c d e = a (b c) (d e)` |
| `E` | Eagle | `E a b c d e = a b (c d e)` |
| `Ê` (alias `E^`) | Bald Eagle | `Ê a b c d e f g = a (b c d) (e f g)` |
| `F` | Finch | `F a b c = c b a` |
| `F*` | Finch Once Removed | `F* a b c d = a d c b` |
| `F**` | Finch Twice Removed | `F** a b c d e = a b e d c` |
| `G` | Goldfinch | `G a b c d = a d (b c)` |
| `H` | Hummingbird | `H a b c = a b c b` |
| `I` | Identity (Idiot) | `I a = a` |
| `I*` | Identity Once Removed | `I* a b = a b` |
| `I**` | Identity Twice Removed | `I** a b c = a b c` |
| `J` | Jay | `J a b c d = a b (a d c)` |
| `K` | Kestrel | `K a b = a` |
| `Ki` | Kite | `Ki a b = b` |
| `KM` | Konstant Mocker | `KM a b = b b` |
| `C(KM)` → name it `KM'` | Crossed Konstant Mocker | `KM' a b = a a` |
| `L` | Lark | `L a b = a (b b)` |
| `M` | Mockingbird | `M a = a a` |
| `M2`/`M₂` | Double Mockingbird | `M₂ a b = a b (a b)` |
| `O` | Owl | `O a b = b (a b)` |
| `Φ` (alias `Phi`) | Phoenix | `Φ a b c d = a (b d) (c d)` |
| `Ψ` (alias `Psi`) | Psi Bird | `Ψ a b c d = a (b c) (b d)` |
| `Q` | Queer Bird | `Q a b c = b (a c)` |
| `Q1`/`Q₁` | Quixotic Bird | `Q₁ a b c = a (c b)` |
| `Q2`/`Q₂` | Quizzical Bird | `Q₂ a b c = b (c a)` |
| `Q3`/`Q₃` | Quirky Bird | `Q₃ a b c = c (a b)` |
| `Q4`/`Q₄` | Quacky Bird | `Q₄ a b c = c (b a)` |
| `R` | Robin | `R a b c = b c a` |
| `R*` | Robin Once Removed | `R* a b c d = a c d b` |
| `R**` | Robin Twice Removed | `R** a b c d e = a b d e c` |
| `S` | Starling | `S a b c = a c (b c)` |
| `T` | Thrush | `T a b = b a` |
| `U` | Turing Bird | `U a b = b (a a b)` |
| `V` | Vireo | `V a b c = c a b` |
| `V*` | Vireo Once Removed | `V* a b c d = a d b c` |
| `V**` | Vireo Twice Removed | `V** a b c d e = a b e c d` |
| `W` | Warbler | `W a b = a b b` |
| `W*` | Warbler Once Removed | `W* a b c = a b c c` |
| `W**` | Warbler Twice Removed | `W** a b c d = a b c d d` |
| `W'`/`W′`/`W¹` | Converse Warbler | `W' a b = b a a` |
| `Y` | Sage Bird | `Y a = a (Y a)` — **recursive**; store explicit `ski` (Curry's `S (K (S I I)) (S (S (K S) K) (K (S I I)))`) |

Θ (Turing fixed point) is a derived alias, preloaded as if the user had typed
`Θ := U U` (ASCII alias `Theta`).

**⚠ Verification requirement.** The implementer MUST cross-check every row of
this table against the two source URLs before shipping (the once-removed
permuting birds and Jay are the classic transcription-error spots) and encode
the sources' SKI/SK columns as test vectors per §12. Where the two sources
disagree on a name, Smullyan/Rathman naming wins. The combinatorylogic.com
extras that have no Smullyan name (Greek-letter forms `Φ₁`, `Σ`, `κ`, …) MAY
be added under their table names; skip any that collide.

---

## 6. Reduction (`reduce.py`)

### 6.1 Strategy

**Normal order = leftmost-outermost**, run to **full normal form**:

1. A *redex* is `X a₁ … aₙ` where `X` is a defined combinator of arity `n`
   (possibly with further args beyond `n`: only the first `n` are consumed;
   `K a b c ⇒ a c`). It contracts by substituting `a₁…aₙ` into `X`'s rule RHS.
   An *alias* head (`:=` definition, arity 0) is a redex by itself and unfolds
   to its body — but only when demanded (see step 3), so aliases stay folded
   in output when they never needed unfolding.
2. Repeatedly contract the **leftmost-outermost** redex: walk the spine; if
   the head is a combinator with enough args, contract there first.
3. If the head atom is an alias, unfold it only if unfolding could enable a
   contraction (i.e., always unfold aliases in head position during reduction;
   an alias in argument position is left alone until reduction reaches it).
4. When the head is stuck (free variable, or under-applied combinator),
   recurse into the arguments left-to-right and normalize each.

This is standard leftmost-outermost normalization: it finds the normal form
whenever one exists, and never evaluates an argument that is discarded —
`K x (M M)` terminates. No sharing/graph reduction in v1 (terms are small);
note it as future work.

Substitution is capture-free trivially: rule RHS variables are a closed set of
formals; combinator terms have no binders.

### 6.2 Fuel and size limits

- `max_steps` (default **10 000**) contractions per evaluation; settable with
  `%fuel N` for the session.
- `max_size` (default **100 000** atoms in the term) guards explosive growth
  (`M M`-style terms grow, `Y`-chains grow); checked after each contraction.
- On exhaustion, the result is **not** an error-status reply: print the
  current (partially reduced) term plus a warning line, e.g.
  `⚠ no normal form after 10000 steps (fuel exhausted); term size 412`
  and, for size, `⚠ term exceeded 100000 atoms after 831 steps`.

### 6.3 Output

Default per expression: normal form, then a dim/bracketed step count:

```
In:  B M (R M B) B
Out: ▲-free normal form here        [7 steps]
```

`0 steps` prints as `[normal form]`. Under `%trace` (per-cell magic, §9) print
every step, numbered, one per line, marking the contracted redex's combinator:

```
    0  K ▲ (M M)
K   1  ▲
```

Trace obeys the same fuel; long traces elide the middle beyond 200 lines
(`… 9600 steps elided …`) unless `%fuel` raised.

---

## 7. Definitions

Two forms, both making the name a first-class combinator for reduction *and*
basis expansion:

- **Alias** — `Name := expr`. Arity 0; unfolds per §6.1. Expr may reference
  built-ins, prior definitions, and free symbols.
- **Rule** — `Name v₁ v₂ … vₙ -> expr`, e.g. `🟢 x y z -> x (z y)`. Arity n.
  Constraints, checked at definition time:
  - `v₁…vₙ` are distinct tokens and must not be currently-defined combinator
    names (error: `variable 'K' shadows a combinator`).
  - Every atom in `expr` is either one of the `vᵢ`, a defined combinator, a
    free symbol (allowed, with an informational note), or `Name` itself
    (**recursion allowed** — enables Y-style birds; such a definition reduces
    fine but cannot be basis-expanded, see §8).

Rules of engagement:

- Redefining a **built-in** bird is an error (`cannot shadow built-in 'B'`).
- Redefining a user definition replaces it, with a notice.
- `%undef Name` removes a user definition.
- Definitions are session-scoped; they die with the kernel. (Persistence via
  `%save`/`%load` of a plain-text defs file is a v1.1 nicety, not required.)
- Successful definition prints e.g. `defined 🟢 (arity 3): 🟢 x y z -> x (z y)`.

---

## 8. Basis expansion (`abstraction.py`)

`expand(term, basis)` rewrites every non-basis combinator atom into the target
basis. For a rule-combinator `X v₁…vₙ -> rhs`: first recursively expand `rhs`
(so definitions-in-terms-of-birds bottom out in S/K/I), then bracket-abstract
the formals right-to-left: `[v₁]…[vₙ] rhs'`. For an alias, expand its body.
Memoize per (combinator, basis); built-ins are expanded on demand.

Bracket abstraction (Curry, with η-optimization), target S/K/I:

```
[x] x            = I
[x] E            = K E                if x not free in E
[x] (E x)        = E                  if x not free in E        (η)
[x] (E F)        = S ([x]E) ([x]F)    otherwise
```

- **S/K target** (`%sk`): post-process `I → S K K`.
- **Recursive definitions** (name free in its own expanded rule, e.g. a
  user-typed sage): expansion is an error —
  `cannot expand recursive combinator '🔁' to a finite S/K/I term; define it
  via a fixed-point combinator (e.g. 🔁 := Y step) instead`. Built-in `Y`
  carries its explicit `ski` override and expands fine.
- Free variables pass through untouched: `%ski Q₁ ▲` →
  `S (K (S I)) K ▲` — expansion does **not** reduce; follow with a plain cell
  to reduce, or use `%skirun` — no: keep orthogonal, expansion never reduces.

Magics: `%ski expr`, `%sk expr` print the expanded term (with step-count line
omitted). `%ski Name` / `%sk Name` on a bare combinator prints its basis form
(this doubles as the "show me the SKI form" affordance).

Optional (v1.1, not required): `%bckw expr` targeting the B/C/K/W basis via
the standard Curry translation.

---

## 9. Magics (`magics.py`)

A magic occupies the whole statement line: `%name [args…]`.

| Magic | Effect |
|---|---|
| `%trace expr` | evaluate with full step-by-step output (§6.3) |
| `%whnf expr` | reduce only to weak head normal form (stop before §6.1 step 4) |
| `%ski expr` / `%sk expr` | basis-expand, no reduction (§8) |
| `%fuel N` | set `max_steps` for the session; bare `%fuel` prints current |
| `%size N` | set `max_size`; bare form prints current |
| `%birds` | table of the registry: symbol, bird name, arity, rule |
| `%whatis X` | one bird/definition card: name(s), bird name, arity, rule, λ-form, S/K/I form |
| `%defs` | list user definitions |
| `%undef X` | remove a user definition |
| `%ascii on\|off` | output script preference: `Q1` vs `Q₁` (default off ⇒ Unicode) |

Unknown magic → error listing available magics. `%birds` and `%whatis` emit
`text/markdown` tables when the frontend supports display_data (fall back to
aligned `text/plain`).

The λ-form shown by `%whatis` is generated from the rule
(`Q₁ = λa b c. a (c b)`), not stored.

---

## 10. Jupyter protocol (`kernel.py`)

`AviaryKernel(Kernel)` with:

- `implementation` `"aviary"`, `language_info`:
  `{"name": "combinatory-logic", "file_extension": ".cl", "mimetype": "text/x-combinatory-logic"}`.
- `do_execute`: run statements per §4.1. Result terms go out as
  `execute_result` with `text/plain` (last expression) / `display_data`
  (earlier ones); warnings and confirmations on the `stderr`/`stdout` streams
  respectively. Parse/definition errors → `error` reply with a readable
  traceback-free message (`ename: "ParseError"` etc.); **fuel exhaustion is
  not an error** (§6.2).
- `do_complete`: complete the token at the cursor against registry names,
  aliases, user definitions, and magic names (when the line starts with `%`).
  Offer both scripts (`Q1` and `Q₁`).
- `do_inspect`: shift-Tab on a name shows the `%whatis` card.
- `do_is_complete`: `incomplete` iff the current line has unclosed `(`;
  `indent` is `""`.
- `do_interrupt`/KeyboardInterrupt during reduction: the reducer checks an
  interrupt flag between contractions and aborts cleanly, printing the
  partial term like fuel exhaustion. **The reducer must be iterative
  (explicit stack), not structurally recursive** — deep spines would blow
  Python's recursion limit.

---

## 11. Errors

All user-facing, no Python tracebacks:

- `ParseError` — with line/col/caret.
- `DefinitionError` — shadowing, duplicate vars, bad LHS.
- `ExpansionError` — recursive combinator (§8).
- `MagicError` — unknown magic / bad args.

---

## 12. Tests & acceptance criteria

`pytest`; all MUST pass.

1. **Parser round-trips**: `parse ∘ pretty ≡ id` on a corpus including
   Unicode names, emoji atoms, nested parens; minimal-parenthesization checks
   (`S K (K I)` not `((S K) (K I))`).
2. **Every bird's rule**: for each registry entry of arity n, apply it to
   fresh free symbols `x₁…xₙ` and assert the exact one-step contraction
   matches the table in §5.2 *and* the rule given by the Wolfram dataset
   (encode the dataset's rules as fixtures cross-checked by a human against
   the URLs — cite them in the fixture file header).
3. **Derived SKI forms are correct**: for each bird, `expand(X, SKI)` applied
   to `x₁…xₙ` must reduce to the same normal form as `X x₁…xₙ`. (This is the
   right check — derived forms may differ syntactically from the published
   columns; published columns from combinatorylogic.com are additionally
   asserted *behaviorally equivalent* the same way, as oracle vectors.)
4. **Laziness**: `K ▲ (M M)` ⇒ `▲` in 1 step; `Ki (M M) ▲` ⇒ `▲`;
   `S K (M M) ▲` terminates. `M M` alone exhausts fuel gracefully.
5. **Normal order to NF**: `B ▲ 🟢 (K ◆ ●)` fully normalizes arguments after
   the head sticks: ⇒ `▲ (🟢 ◆)`.
6. **Y**: `%trace`-style bounded check that `Y f` unfolds to `f (Y f)` in one
   step, and that `expand(Y)` applied to `f` reduces (bounded) to a term whose
   head is `f`.
7. **Definitions**: rule definition reduces and `%ski`-expands; alias stays
   folded when unused (`K ▲ MyAlias` ⇒ `▲` with `MyAlias` never unfolded);
   recursive user definition reduces but `%ski` raises `ExpansionError`;
   shadowing errors.
8. **Fuel/size/interrupt**: exhaustion returns partial term + warning, not an
   error reply; interrupt mid-`M M` leaves the kernel usable.
9. **Kernel end-to-end** (`jupyter_client`): execute a cell, get
   `execute_result`; completion returns `Q₁` for prefix `Q`; `do_is_complete`
   on `B (S`.
10. **Name normalization**: `Q₁ ≡ Q1`, `W′ ≡ W' ≡ W¹`, `E^ ≡ Ê` all resolve
    to the same bird; `%ascii` toggles output script.

Acceptance demo notebook (`demo.ipynb`, committed): the Mockingbird fondness
theorem (`C B M ▲` etc.), a `%trace` of `Φ` in action, defining `🟢`, and
`%ski Q₁` — serving as living documentation.

---

## 13. Non-goals / future work (v1.1+)

- Graph reduction / sharing (call-by-need); v1 is tree rewriting.
- `%bckw` target basis; λ-term *input* (we only output λ-forms in `%whatis`).
- `%save` / `%load` of definitions.
- LaTeX (`text/latex`) rendering of terms.
- Juxtaposition parsing (`SKK` ≡ `S K K`) — deliberately rejected (§4.2).
