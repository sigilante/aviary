"""Term model for Aviary: binary application trees over atoms.

Term = Atom | App

Atoms are simple immutable value objects identified by their canonical
name (see parser.py §4.3 for canonicalization rules). Whether an atom
names a combinator is *not* stored on the atom -- that's determined at
reduction/expansion time by looking the name up in the birds registry
and the session's user definitions, so a symbol defined after a term is
entered still takes effect (SPEC.md §3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, Union


@dataclass(frozen=True)
class Atom:
    name: str

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Atom({self.name!r})"


@dataclass(frozen=True)
class App:
    fn: "Term"
    arg: "Term"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"App({self.fn!r}, {self.arg!r})"


Term = Union[Atom, App]


def atom(name: str) -> Atom:
    return Atom(name)


def apply(fn: Term, *args: Term) -> Term:
    """Left-fold a head applied to a sequence of arguments."""
    result = fn
    for a in args:
        result = App(result, a)
    return result


def spine(term: Term) -> tuple[Term, list[Term]]:
    """Decompose ``term`` into (head, args) by walking the .fn chain.

    Iterative (no recursion): the head is whatever the leftmost
    non-application node is (an Atom, given the grammar), and args are
    in left-to-right application order.
    """
    args: list[Term] = []
    cur = term
    while isinstance(cur, App):
        args.append(cur.arg)
        cur = cur.fn
    args.reverse()
    return cur, args


def size(term: Term) -> int:
    """Count atoms in a term, iteratively (explicit stack)."""
    count = 0
    stack = [term]
    while stack:
        t = stack.pop()
        if isinstance(t, Atom):
            count += 1
        else:
            stack.append(t.fn)
            stack.append(t.arg)
    return count


def free_vars(term: Term) -> set[str]:
    """All atom names occurring in ``term`` (iterative)."""
    names: set[str] = set()
    stack = [term]
    while stack:
        t = stack.pop()
        if isinstance(t, Atom):
            names.add(t.name)
        else:
            stack.append(t.fn)
            stack.append(t.arg)
    return names


def substitute(term: Term, mapping: dict[str, Term]) -> Term:
    """Substitute atoms by name per ``mapping``. No binders in combinator
    terms, so this is capture-free trivially (SPEC.md §6.1). Iterative,
    explicit-stack rebuild via a postorder worklist.
    """
    if not mapping:
        return term
    # Iterative postorder transform using an explicit stack of frames.
    # frame: (term, child_index) while building results bottom-up.
    result_stack: list[Term] = []
    work: list[tuple[Term, bool]] = [(term, False)]
    while work:
        t, expanded = work.pop()
        if isinstance(t, Atom):
            result_stack.append(mapping.get(t.name, t))
            continue
        if not expanded:
            work.append((t, True))
            work.append((t.arg, False))
            work.append((t.fn, False))
        else:
            new_arg = result_stack.pop()
            new_fn = result_stack.pop()
            if new_fn is t.fn and new_arg is t.arg:
                result_stack.append(t)
            else:
                result_stack.append(App(new_fn, new_arg))
    return result_stack.pop()


# --- Pretty printing ------------------------------------------------------

DisplayFn = Callable[[str], str]


def _default_display(name: str) -> str:
    return name


def pretty(term: Term, display: DisplayFn = _default_display) -> str:
    """Render ``term`` with left-associative implicit application,
    parenthesizing only right-nested applications (SPEC.md §3).

    Iterative to avoid recursion-depth issues on deep spines/args. Uses a
    positional result stack (not an id()-keyed cache) so that terms with
    shared subterms -- e.g. the extremely common `M x -> App(x, x)` where
    both children are literally the same object -- print correctly instead
    of double-popping a single cache entry.
    """
    result_stack: list[tuple[str, bool]] = []  # (text, was_app)
    work: list[tuple[Term, bool]] = [(term, False)]
    while work:
        t, expanded = work.pop()
        if isinstance(t, Atom):
            result_stack.append((display(t.name), False))
            continue
        if not expanded:
            work.append((t, True))
            work.append((t.arg, False))
            work.append((t.fn, False))
        else:
            # Push order was (t, True), (t.arg, ...), (t.fn, ...) i.e. arg is
            # on top of `work` and thus processed (and pushed to
            # result_stack) *before* fn -- so on the result stack fn ends up
            # on top and must be popped first here.
            arg_str, arg_is_app = result_stack.pop()
            fn_str, _ = result_stack.pop()
            if arg_is_app:
                arg_str = f"({arg_str})"
            result_stack.append((f"{fn_str} {arg_str}", True))
    return result_stack.pop()[0]
