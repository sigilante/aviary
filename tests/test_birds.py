"""SPEC.md §12 items 2, 3, 10: bird-registry correctness.

Sources and the one correction found are documented in fixtures_birds.py.
"""

from __future__ import annotations

import pytest

from aviary_kernel.abstraction import expand, expand_sk
from aviary_kernel.birds import BIRDS, BY_NAME
from aviary_kernel.environment import Environment
from aviary_kernel.parser import parse_cell
from aviary_kernel.reduce import reduce
from aviary_kernel.terms import Atom, apply, pretty

from .fixtures_birds import RATHMAN_RULE, RATHMAN_SK, CL_ORACLE


def _parse_expr(src: str):
    return parse_cell(src)[0].expr


def _fresh_vars(n: int) -> list[Atom]:
    return [Atom(f"x{i}") for i in range(n)]


@pytest.mark.parametrize("bird", BIRDS, ids=lambda b: b.name)
def test_rule_matches_table_exactly(bird):
    """Every registry rule, applied to fresh free vars, matches SPEC.md
    §5.2's *one-step* contraction (SPEC.md §12 item 2: "apply it to
    fresh free symbols x1...xn and assert the exact one-step
    contraction matches the table"). We use a single-step WHNF reduction
    (not a full run to normal form) precisely so this works uniformly
    for Y too, whose own rule is self-referential and would otherwise
    never reach a normal form."""
    frees = _fresh_vars(bird.arity)
    names = [a.name for a in frees]
    lhs = apply(Atom(bird.name), *frees)
    formal_map = {f: n for f, n in zip(bird.formals, names)}
    substituted = pretty(bird.rule, display=lambda nm: formal_map.get(nm, nm))
    expected_term = _parse_expr(substituted)
    env = Environment()
    res = reduce(lhs, env, max_steps=1, whnf_only=True)
    assert res.steps == 1
    assert pretty(res.term) == pretty(expected_term), (
        f"{bird.name}: contraction {pretty(res.term)!r} != table rule {pretty(expected_term)!r}"
    )


@pytest.mark.parametrize("bird", BIRDS, ids=lambda b: b.name)
def test_rule_matches_rathman_source(bird):
    """Cross-check against Chris Rathman's chart (the Wolfram dataset's
    own cited primary source; see fixtures_birds.py header) -- SPEC.md
    §12 item 2."""
    if bird.name not in RATHMAN_RULE:
        pytest.skip(f"{bird.name} not present in the Rathman fixture")
    expected = RATHMAN_RULE[bird.name]
    frees = _fresh_vars(bird.arity)
    formal_map = {f: v.name for f, v in zip(bird.formals, frees)}
    # our rule, renamed a,b,c -> x0,x1,x2 in the same order Rathman uses
    ours = pretty(bird.rule, display=lambda nm: formal_map.get(nm, nm))
    theirs = pretty(_parse_expr(expected), display=lambda nm: formal_map.get(nm, nm))
    assert ours == theirs, f"{bird.name}: SPEC/registry rule {ours!r} != Rathman {theirs!r}"


@pytest.mark.parametrize("bird", [b for b in BIRDS if b.ski is None], ids=lambda b: b.name)
def test_derived_ski_form_is_behaviorally_correct(bird):
    """SPEC.md §12 item 3: expand(X, SKI) applied to fresh vars reduces to
    the same normal form as X applied to the same vars. Y (the only bird
    with an explicit `ski` override) is excluded here -- it's
    self-recursive, so neither side reaches a normal form on fresh free
    vars; see test_y_ski_override_is_curry_standard_form and
    test_y_expand_reduces_to_head_f below for its dedicated, bounded
    checks."""
    env = Environment()
    frees = _fresh_vars(bird.arity)
    lhs = apply(Atom(bird.name), *frees)
    ski_head = expand(Atom(bird.name), env)
    rhs = apply(ski_head, *frees)
    r1 = reduce(lhs, env, max_steps=2000, max_size=50_000)
    r2 = reduce(rhs, env, max_steps=2000, max_size=50_000)
    assert pretty(r1.term) == pretty(r2.term), (
        f"{bird.name}: direct {pretty(r1.term)!r} != SKI-expanded {pretty(r2.term)!r}"
    )


@pytest.mark.parametrize("bird_name", sorted(RATHMAN_SK.keys()))
def test_rathman_sk_oracle_behaviorally_equivalent(bird_name):
    """Rathman's own fully-expanded S/K column, as an independent oracle
    (SPEC.md §12 item 3)."""
    bird = BY_NAME[bird_name]
    env = Environment()
    frees = _fresh_vars(bird.arity)
    lhs = apply(Atom(bird.name), *frees)
    oracle_term = _parse_expr(RATHMAN_SK[bird_name])
    rhs = apply(oracle_term, *frees)
    r1 = reduce(lhs, env, max_steps=2000, max_size=50_000)
    r2 = reduce(rhs, env, max_steps=2000, max_size=50_000)
    assert pretty(r1.term) == pretty(r2.term), (
        f"{bird_name}: direct {pretty(r1.term)!r} != Rathman-SK oracle {pretty(r2.term)!r}"
    )


@pytest.mark.parametrize("bird_name", sorted(CL_ORACLE.keys()))
def test_combinatorylogic_oracle_behaviorally_equivalent(bird_name):
    """combinatorylogic.com's CR1 column, as a second independent oracle
    (SPEC.md §12 item 3)."""
    bird = BY_NAME[bird_name]
    env = Environment()
    frees = _fresh_vars(bird.arity)
    lhs = apply(Atom(bird.name), *frees)
    oracle_term = _parse_expr(CL_ORACLE[bird_name])
    rhs = apply(oracle_term, *frees)
    r1 = reduce(lhs, env, max_steps=2000, max_size=50_000)
    r2 = reduce(rhs, env, max_steps=2000, max_size=50_000)
    assert pretty(r1.term) == pretty(r2.term), (
        f"{bird_name}: direct {pretty(r1.term)!r} != combinatorylogic.com oracle {pretty(r2.term)!r}"
    )


def test_y_ski_override_is_curry_standard_form(env):
    y = BY_NAME["Y"]
    assert y.ski is not None
    expected = _parse_expr("S (K (S I I)) (S (S (K S) K) (K (S I I)))")
    assert pretty(y.ski) == pretty(expected)


def test_y_expand_reduces_to_head_f(env):
    f = Atom("f")
    ski = expand(Atom("Y"), env)
    term = apply(ski, f)
    res = reduce(term, env, max_steps=50, whnf_only=True)
    # head should be f applied to (something) -- i.e. Y f behaves as f (Y f)
    from aviary_kernel.terms import spine
    head, args = spine(res.term)
    assert head == f


def test_theta_is_u_u(env):
    from aviary_kernel.birds import BUILTIN_ALIASES
    name, body = BUILTIN_ALIASES["Θ"]
    assert pretty(body) == "U U"


# --- SPEC.md §12 item 10: name normalization ------------------------------


@pytest.mark.parametrize("variants", [
    ("Q1", "Q₁"),
    ("W'", "W′", "W¹"),
    ("E^", "Ê"),
])
def test_name_variants_resolve_to_same_bird(variants):
    resolved = set()
    for v in variants:
        stmt = parse_cell(v)[0]
        assert stmt.expr.name in BY_NAME or stmt.expr.name in BY_NAME
        resolved.add(BY_NAME[stmt.expr.name].name)
    assert len(resolved) == 1


def test_ascii_toggle_changes_display(env):
    term = _parse_expr("Q1")
    env.ascii_mode = False
    assert env.pretty(term) == "Q₁"
    env.ascii_mode = True
    assert env.pretty(term) == "Q1"


def test_sk_target_replaces_i_with_skk(env):
    result = expand_sk(Atom("I"), env)
    assert pretty(result) == "S K K"
    # no bare I anywhere in an %sk expansion
    assert "I" not in {a for a in _atoms(result)}


def _atoms(term):
    from aviary_kernel.terms import free_vars
    return free_vars(term)
