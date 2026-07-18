# Aviary

A Jupyter kernel for **combinatory logic** (combinator calculus): S/K/I,
BCKW, and the Smullyan aviary (Bluebird, Cardinal, Mockingbird, Phoenix,
Psi, Vireo, the once- and twice-removed permuting birds, and more),
evaluated under normal-order (leftmost-outermost, lazy) reduction to
full normal form.

```
K ▲ (M M)
```
```
▲        [1 step]
```

`M M` (the classic non-terminating self-application) is never touched --
that's normal order's laziness in action. See `SPEC.md` for the full
design and `demo.ipynb` for a guided tour, including a computational
proof-sketch of Smullyan's Mockingbird fondness theorem.

## Install

Requires Python >= 3.10.

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m aviary_kernel.install --user   # or --prefix /path/to/env
```

This registers a kernelspec named `aviary`, displayed as
**"Aviary (Combinator Calculus)"** in Jupyter frontends. Then:

```sh
jupyter notebook demo.ipynb        # open the demo
jupyter console --kernel aviary    # or drop into a REPL
```

(`--user` installs into your per-user Jupyter kernel directory;
`--prefix .venv` installs into the active virtualenv instead, which is
handy for local development without touching your global Jupyter
config.)

## Usage

A cell is a sequence of lines; each non-empty line is one statement: a
**magic** (`%name ...`), a **definition** (`Name := expr` or
`Name v1 v2 -> expr`), or an **expression**. `#` starts a comment.

### Expressions

Application is left-associative and implicit -- `S K K` means
`((S K) K)`. Parentheses group; `S K (K I)` differs from `S (K (K I))`.
Any built-in bird, or arbitrary Unicode atom (`▲`, `🟢`, `foo_bar`), can
appear free:

```
B ▲ 🟢 (K ◆ ●)
```
```
▲ (🟢 ◆)        [2 steps]
```

Names like `Q1`/`Q₁`, `W'`/`W′`/`W¹`, and `E^`/`Ê` are the same bird
under Unicode normalization (subscript digits, primes, superscript one)
and explicit ASCII aliases; `%ascii on`/`off` picks which script output
uses.

### Definitions

```
🟢 x y z -> x (z y)      # rule (a new combinator of arity 3)
Theta := U U             # alias (already preloaded, for reference)
```

Rules can be recursive (the name may appear in its own body -- that's
how you'd hand-roll a sage bird); recursive definitions reduce fine but
can't be basis-expanded to a finite S/K/I term (`%ski` raises an error
explaining why, and suggests routing through `Y`/`Θ` instead). Redefining
a *built-in* is an error; redefining a *user* definition replaces it.
`%undef Name` removes a user definition; `%defs` lists them all.

### Magics

| Magic | Effect |
|---|---|
| `%trace expr` | step-by-step reduction trace |
| `%whnf expr` | reduce to weak head normal form only |
| `%ski expr` / `%sk expr` | basis-expand to S/K/I (or strict S/K); does not reduce |
| `%fuel N` | set the step budget for the session (bare form prints it) |
| `%size N` | set the term-size guard (bare form prints it) |
| `%birds` | table of the whole registry |
| `%whatis X` | one bird/definition's name(s), arity, rule, λ-form, and S/K/I form |
| `%defs` | list user definitions |
| `%undef X` | remove a user definition |
| `%ascii on\|off` | toggle `Q1` vs `Q₁`-style output |

Reduction is fuel-bounded (10 000 steps and 100 000 atoms by default);
running out is a *warning*, not an error -- you get the partial term
back and can raise the budget with `%fuel`/`%size` and try again:

```
M M
```
```
M M      [10000 steps]
⚠ no normal form after 10000 steps (fuel exhausted); term size 3
```

## Examples

**Bracket abstraction is derived, not hand-copied.** Every non-recursive
bird's S/K/I form comes from Curry's bracket-abstraction algorithm
applied to its rule, on demand:

```
%ski Q₁
```
```
S (S (K S) (S (K K) (S (K S) K))) (K (S (K (S I)) K))
```

**`%trace` shows normal order at work**, including descent into stuck
arguments once the head sticks:

```
%trace Φ B C K x y
```
```
    0  Φ B C K x y
Φ   1  B (C x) (K x) y
B   2  C x (K x y)
K   3  C x x
```

## Package layout

```
aviary_kernel/
  terms.py        Term model (Atom | App), pretty-printer
  parser.py        lexer + parser -> Term
  birds.py          the bird registry (verified against two independent sources; see below)
  reduce.py          normal-order reducer: iterative, fuel/size/interrupt-checked
  abstraction.py    bracket abstraction -> S/K/I (and S/K)
  magics.py          %-command dispatch
  kernel.py          AviaryKernel(ipykernel.kernelbase.Kernel)
  install.py         `python -m aviary_kernel.install` writes the kernelspec
  kernelspec/         kernel.json
tests/               pytest suite (parser, birds, reduce, abstraction, kernel end-to-end)
demo.ipynb            living documentation / acceptance demo
SPEC.md               the full design spec
```

## Development

```sh
pip install -e '.[test]'
pytest                       # full suite
python -m aviary_kernel.install --prefix .venv   # register the kernel into this venv
```

The bird registry (`birds.py`) was cross-checked row by row against the
Wolfram Data Repository's *Combinator Birds* dataset (via its own cited
primary source, Chris Rathman's chart, fetched through the Wayback
Machine) and combinatorylogic.com's table -- see the header of
`tests/fixtures_birds.py` for the two source discrepancies that surfaced
during verification (and how they were resolved) and `tests/test_birds.py`
for the resulting behavioral-equivalence oracles.

## Non-goals (v1)

Graph reduction/sharing (this is tree rewriting -- fine at the term
sizes a REPL session produces); a `%bckw` target basis; λ-term input;
`%save`/`%load` of definitions; LaTeX rendering; juxtaposition parsing
(`SKK` is one atom, not `S K K` -- deliberate, see `SPEC.md` §4.2/§13).
