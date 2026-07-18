# Aviary desk — a combinator-calculus Caderno kernel for Urbit

**Status:** specification, ready for implementation.
**Substrate:** Hoon; a `/lib/shoe` Gall agent (`%aviary`) implementing caderno's
`%eval-command` kernel contract. Modeled on North
(`~/urbit/north`, **branch `master`** — not the currently checked-out branch,
which dropped the eval-command support).
**Scope:** the "core + definitions" subset of `SPEC.md` — same language, same
semantics; a sibling of the Python Jupyter kernel, not a dependency of it.

This file lives at the repo root, not inside `desk/`, because every file in an
installed desk needs a Clay mark.

---

## 1. Overview

The `desk/` directory is a self-contained, installable Urbit desk providing the
`%aviary` agent: a combinator-calculus REPL over `/lib/shoe`, usable

- interactively from a terminal session, and
- as a **caderno kernel** (see `~/urbit/caderno/README.md`): caderno subscribes
  to `/sole/[ship]/[ses]`, pokes `%eval-command` `[ses=@ta src=tape]`, and
  consumes `%sole-effect` facts — `%txt` lines as output, terminal `%pro` as
  completion. Kernel discovery uses the `/x/sole/sessions` scry.

Both the `%eval-command` handler and the `/x/sole/sessions` scry live in the
**vendored `lib/shoe.hoon` from North master** — the agent itself needs no
special code for either.

### v1 scope (from SPEC.md)

**In:** expressions over the full 50-bird registry + arbitrary Unicode atoms;
normal-order reduction to normal form with fuel/size bounds; user definitions
(`:=` aliases and `->` rules, per SPEC.md §7); basis expansion; magics
`%ski` `%sk` `%fuel` `%defs` `%undef`.

**Deferred (v1.1):** `%trace`, `%whnf`, `%birds`, `%whatis`, `%ascii`,
completion/tab-list beyond shoe's default.

---

## 2. Repo layout

```
desk/
  sys.kelvin              # [%zuse 408]
  desk.bill               # :~  %aviary  ==
  app/aviary.hoon         # shoe agent (~120 lines; north master's app/north.hoon is the template)
  lib/aviary.hoon         # the pure engine — everything in §4
  lib/shoe.hoon           # VENDORED from base master
  lib/sole.hoon           # VENDORED from base master
  lib/default-agent.hoon  # VENDORED from base master
  lib/dbug.hoon           # VENDORED from base master
  lib/skeleton.hoon       # VENDORED from base master (dbug dep)
  sur/aviary.hoon         # any particular types
  sur/sole.hoon           # VENDORED from base master
  mar/eval-command.hoon   # VENDORED from base master
tests/
  test-engine.sh          # headless engine tests via `urbit eval` (§8)
Makefile                  # `make test` = pytest (Python), `make test-hoon` = tests/test-engine.sh
```

Vendor files byte-for-byte from base master; do not edit them. If a vendored
file must change, that's a finding to report, not a local patch to make
silently.

---

## 3. Language

Identical to `SPEC.md` §§3–7 within the v1 scope. Statement forms per line:
expression, `Name := expr`, `Name v₁ … vₙ -> expr`, or a magic (`%`-initial
first token). `#` comments. Application by juxtaposition with **mandatory
whitespace between atoms**, parens for grouping, left-associative.

The five magics: `%ski expr`, `%sk expr` (expansion only, never reduces;
`%sk` additionally rewrites `I → S K K`), `%fuel [N]` (set/show session fuel),
`%defs`, `%undef Name`. Unknown magic → error listing the five.

---

## 4. Engine — `lib/aviary.hoon` and `sur/aviary.hoon`

A pure library, no Gall/agent imports. Public shape (names indicative), with types in /sur/aviary.hoon and ++run in /lib/aviary.hoon:

```hoon
+$  term  $%([%atom name=@t] [%app fun=term arg=term])
+$  bird  [name=@t disp=@t arity=@ud rule=tape]      ::  rule = canonical text, parsed on demand
+$  def   $%([%alias body=term] [%rule arity=@ud vars=(list @t) rhs=term])
+$  env   [defs=(map @t def) fuel=@ud]               ::  per-session state
++  run   |=([env line=tape] [out=(list tape) =env]) ::  the single entry point
```

`++run` executes one statement and returns output lines; the agent stays a
transport shim.

### 4.1 Lexing and Unicode

Input arrives as a **UTF-8 `tape`**. Decode to codepoints with `+turf` (→
`(list @c)`); lex over codepoints; re-encode token names to `@t` cords with
`+tuft`/`+taft` composition. Token rule as in SPEC.md §4.2: any maximal run of
codepoints that aren't whitespace, `(`, or `)`; `(`/`)` are always their own
tokens. No single-letter special-casing — `SKK` is one (free-variable) atom.

Name canonicalization (SPEC.md §4.3), **Hoon deviation**: the stdlib has no
Unicode normalization, so apply only these targeted codepoint maps —
subscript digits U+2080–U+2089 → ASCII digits, `′` U+2032 → `'`, `¹` U+00B9 →
`'`. No general NFC: a decomposed `E`+U+0302 will *not* match `Ê` (precomposed
`Ê` and the ASCII alias `E^` both work). Document this in a comment.

Malformed UTF-8 must produce a parse error, not a crash.

### 4.2 Registry

Hand-written (per project decision), as a **strictly formatted literal list**
that the Python suite cross-checks (§7). One bird per line, exactly:

```hoon
++  birds
  ^-  (list bird)
  :~  ['B' 'B' 3 "a (b c)"]
      ['B1' 'B₁' 4 "a (b c d)"]
      ['Q1' 'Q₁' 3 "a (c b)"]
      ...
  ==
```

- Column 1: canonical ASCII name; column 2: display name (Unicode subscripts);
  column 3: arity; column 4: the rule RHS in canonical text over formal
  variables `a b c d e f g`, **parsed by the engine's own parser** the first
  time each bird is used (or eagerly into a map at first call — either way,
  the source of truth is the text, so the cross-test and the code cannot
  disagree, and the engine parser gets exercised on all 50 rules).
- Contents: exactly the 50 birds of `SPEC.md` §5.2, same names/arities/rules —
  the Python `aviary_kernel/birds.py` registry is the verified reference; do
  not re-derive from external sources. Aliases (`E^` for `Ê`, `Phi`/`Psi` for
  `Φ`/`Ψ`, `Theta` for `Θ`) in a small separate alias list.
- `Y` additionally carries its explicit S/K/I override
  (`"S (K (S I I)) (S (S (K S) K) (K (S I I)))"`, Curry's form, same as
  Python) — bracket abstraction diverges on it. `Θ` is a preloaded alias for
  `U U`, not a registry row.

### 4.3 Reduction

Normal order per SPEC.md §6.1: leftmost-outermost to full normal form; a
combinator applied to ≥ arity args contracts; aliases unfold only in head
position on demand; stuck heads → normalize arguments left-to-right.

- **Fuel** default `10.000` steps and **size cap** `100.000` atoms, per
  evaluation; fuel is session-adjustable via `%fuel`, size cap fixed. These
  bounds are *mandatory* — an unbounded `M M` would wedge the Gall event.
- Implement the reducer as an explicit-stack loop (a spine zipper), not naive
  structural recursion — deep spines and long reductions must not depend on
  stack depth.
- Exhaustion is output, not a crash: print the partial term plus
  `⚠ no normal form after N steps (fuel exhausted)` /
  `⚠ term exceeded 100000 atoms after N steps`.

### 4.4 Basis expansion, definitions, output

- Bracket abstraction (Curry + η) exactly as SPEC.md §8; derived for every
  non-`Y` bird and for user rules; alias bodies expanded recursively;
  a recursive definition → error text
  `! cannot expand recursive combinator '…' to a finite S/K/I term`.
- Definitions per SPEC.md §7: shadowing a built-in errors; redefining a user
  def replaces with a notice; success prints
  `defined 🟢 (arity 3): 🟢 x y z -> x (z y)`.
- Pretty-printer: minimal parens, display names (Unicode) for registry atoms,
  free variables verbatim. Results print as `<term>  [N steps]`
  (`[normal form]` when N=0). **Numbers in output are plain digits** — do not
  use `scot %ud` (it renders 10000 as `10.000`); write a small digit-renderer.
- Errors are lines prefixed `! ` (north's convention); warnings `⚠ `.

---

## 5. Agent — `app/aviary.hoon`

Copy north master's `app/north.hoon` structure (113 lines) with these deltas:

- State: `[%0 sessions=(map sole-id:shoe env)]`. Envs are created lazily on
  first command with default fuel; they persist in agent state across
  restarts, and since caderno uses one sole session per notebook, definitions
  are naturally **per-notebook**. (`on-load`: identity for `%0`.)
- `++command-parser`: `(stag | (star next))` — **not** `(star prn)`, which is
  ASCII-only and would reject `Q₁`/`▲`/`🟢` at the keystroke-parser layer
  before the engine ever sees them. The engine does all real parsing.
- `++on-command`: look up/create the session env, call `++run`, emit each
  output line as `[%shoe ~[sole-id] %sole %txt line]`, store the updated env.
  No echo of input; no `%pro` from the agent (the interactive path prompts via
  shoe; the `%eval-command` path appends its own terminal `%pro` in the
  vendored wrapper).
- `++can-connect`: `=(our src):bowl`.
- Keep `dbug`; keep `on-poke on-poke:def` etc. — `%eval-command` and
  `%sole-action` are handled by the vendored shoe wrapper before the inner
  agent sees them.

---

## 6. Installation

README section (extend the existing README.md with an "Urbit / Caderno" section):

```
:: on a ship with the desk synced to %aviary
|install our %aviary
:: caderno: create a notebook, choose kernel "aviary"
```

Plus the standard dev loop: `|mount %aviary`, rsync `desk/` into the pier
mount, `|commit %aviary`. Note the caderno-side requirement from its README:
kernel *discovery* needs the `/x/sole/sessions` scry, which our vendored shoe
provides.

---

## 7. Registry cross-test (Python side)

Add `tests/test_hoon_registry.py` to the **existing Python suite** (per
project decision: hand-written Hoon registry, sync enforced by test):

- Parse `desk/lib/aviary.hoon` with a line regex matching the §4.2 format
  exactly (the format is a contract; a registry line that doesn't match the
  regex is itself a test failure).
- Assert the extracted set of (ascii-name, display-name, arity,
  canonical-rule-text) **equals** the Python registry's, where the Python side
  renders each bird's rule via its own pretty-printer in canonical ASCII with
  variables `a b c …` — so both sides derive the comparison string from their
  actual data, and any drift in either direction fails.
- Assert Y's Hoon override string equals the Python `Y.ski` pretty-printed.
- Hard-fail (never skip) on a bird present on one side only.
- When these are correct, produce /desk/tests/lib/aviary.hoon with the full suite of combinators.

---

## 8. Hoon engine tests

`tests/test-engine.sh`, following north master's `tests/test-nock.sh` pattern:
build `=>`-pipelines of `desk/lib/aviary.hoon` + a test expression, run
through `urbit eval` (`$URBIT_BIN`, defaulting to `~/bin/urbit`, falling back
to `urbit` on PATH), grep the result. Keep each case one focused expression;
prefer a single Hoon expression that returns a list of failing case labels
(empty list = pass) over 50 separate `urbit eval` spawns, since each spawn
costs seconds. MUST cover:

1. **Every bird, one step**: for each registry row, applying the bird to fresh
   free atoms `x1 … xn` contracts to exactly the parsed rule text.
2. **Laziness**: `K ▲ (M M)` ⇒ `▲` in 1 step; `S K (M M) ▲` ⇒ `▲`;
   `M M` alone exhausts fuel with the `⚠` line, no crash.
3. **Full normalization**: `B ▲ 🟢 (K ◆ ●)` ⇒ `▲ (🟢 ◆)` (Unicode atoms
   round-trip through the whole pipeline).
4. **Definitions**: rule def reduces and `%ski`-expands; alias stays folded
   when unused; shadowing a built-in errors; recursive def reduces but `%ski`
   errors; `%undef` works.
5. **Expansion soundness**: for a sample of ≥10 birds spanning arities 1–7
   (include `Ê`, `W'`, `Q₄`, `Y`), `%ski`-expanded form applied to fresh
   atoms reduces to the same normal form as the bird itself. (The Python suite
   already proves this for all 50 via the same abstraction algorithm; the
   sample guards the Hoon port.)
6. **Statement plumbing**: `%fuel 50` then `M M` stops at 50; `%defs` lists;
   comments and blank lines are no-ops; unknown magic errors.

Wire as `make test-hoon`. The agent layer (§5) is deliberately thin enough
that engine tests + caderno acceptance cover it; no headless Gall harness
required.

---

## 9. Acceptance (manual checklist, documented in README)

On a fakezod with both desks installed: `%aviary` appears in caderno's kernel
discovery; a notebook with kernel `aviary` runs `K ▲ (M M)` ⇒ `▲  [1 step]`;
a definition made in one notebook is visible in that notebook's later cells
but not in a different notebook (separate session); `%ski Q₁` prints the
derived form; a fuel-exhausting cell shows the `⚠` line and the notebook stays
responsive.

---

## 10. Non-goals / future (v1.1+)

- Deferred magics (§1) — `%trace` first; sole output is line-oriented, so it
  ports directly.
- `.ipynb` ⇄ `cnb` conversion of aviary notebooks (caderno's FORMAT.md notes
  the kinship).
- Sharing/graph reduction; `%bckw` target basis (same status as Python side).
- Upstreaming `%eval-command` to `/lib/shoe` proper (tracked by caderno README
  and urbit/urbit#7379).
