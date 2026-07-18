"""Basis expansion: rewrite any term into the pure S/K/I basis (or strict
S/K) via Curry bracket abstraction with the eta-optimization (SPEC.md §8).

Only Y (and, transitively, anything built from Y) is stored with an
explicit basis override; every other combinator's S/K/I form is
*derived* here from its `rule`/definition body, never hand-copied.
"""

from __future__ import annotations

from .environment import Environment
from .terms import Atom, App, Term, free_vars

S = Atom("S")
K = Atom("K")
I = Atom("I")

_SKI_BASIS_NAMES = {"S", "K", "I"}


class ExpansionError(Exception):
    pass


def bracket_abstract(x: str, body: Term) -> Term:
    """Curry's bracket abstraction with eta-optimization (SPEC.md §8):

        [x] x        = I
        [x] E        = K E              if x not free in E
        [x] (E x)    = E                if x not free in E   (eta)
        [x] (E F)    = S ([x]E) ([x]F)  otherwise
    """
    if isinstance(body, Atom):
        if body.name == x:
            return I
        return App(K, body)
    # body is App(E, F)
    e, f = body.fn, body.arg
    if x not in free_vars(body):
        return App(K, body)
    if isinstance(f, Atom) and f.name == x and x not in free_vars(e):
        return e
    return App(App(S, bracket_abstract(x, e)), bracket_abstract(x, f))


def expand(term: Term, env: Environment) -> Term:
    """Expand every non-basis combinator atom in ``term`` into S/K/I.
    Does not reduce. Memoized per combinator name on ``env``."""
    return _expand(term, env, in_progress=())


def _expand(term: Term, env: Environment, in_progress: tuple[str, ...]) -> Term:
    if isinstance(term, App):
        return App(_expand(term.fn, env, in_progress), _expand(term.arg, env, in_progress))
    # Atom
    name = term.name
    if name in _SKI_BASIS_NAMES:
        return term
    if name in env.expansion_cache:
        return env.expansion_cache[name]
    comb = env.lookup(name)
    if comb is None:
        return term  # free variable, passes through untouched
    if name in in_progress:
        raise ExpansionError(
            f"cannot expand recursive combinator '{name}' to a finite S/K/I "
            f"term; define it via a fixed-point combinator (e.g. {name} := "
            f"Y step) instead"
        )
    if comb.ski is not None:
        # Explicit override (Y). Already closed over S/K/I; still run
        # through _expand in case it references other combinators (it
        # doesn't, for Y, but this keeps the mechanism general).
        result = _expand(comb.ski, env, in_progress + (name,))
        env.expansion_cache[name] = result
        return result
    next_in_progress = in_progress + (name,)
    if comb.is_alias:
        result = _expand(comb.body, env, next_in_progress)
    else:
        expanded_body = _expand(comb.body, env, next_in_progress)
        result = expanded_body
        for formal in reversed(comb.formals):
            result = bracket_abstract(formal, result)
    env.expansion_cache[name] = result
    return result


def _replace_i_with_skk(term: Term) -> Term:
    if isinstance(term, Atom):
        if term.name == "I":
            return App(App(S, K), K)
        return term
    return App(_replace_i_with_skk(term.fn), _replace_i_with_skk(term.arg))


def expand_sk(term: Term, env: Environment) -> Term:
    """Basis-expand to strict S/K (SPEC.md §8): expand to S/K/I, then
    post-process I -> S K K."""
    return _replace_i_with_skk(expand(term, env))
