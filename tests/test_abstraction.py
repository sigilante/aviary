"""Bracket abstraction / basis expansion (SPEC.md §8)."""

from __future__ import annotations

import pytest

from aviary_kernel.abstraction import expand, expand_sk, bracket_abstract, ExpansionError
from aviary_kernel.environment import Environment
from aviary_kernel.parser import parse_cell
from aviary_kernel.reduce import reduce
from aviary_kernel.terms import Atom, apply, pretty, free_vars


def _e(src: str):
    return parse_cell(src)[0].expr


def test_bracket_abstract_identity():
    # [x] x = I
    result = bracket_abstract("x", Atom("x"))
    assert pretty(result) == "I"


def test_bracket_abstract_constant():
    # [x] E = K E, x not free in E
    result = bracket_abstract("x", Atom("y"))
    assert pretty(result) == "K y"


def test_bracket_abstract_eta():
    # [x] (E x) = E, x not free in E
    result = bracket_abstract("x", apply(Atom("f"), Atom("x")))
    assert pretty(result) == "f"


def test_bracket_abstract_general_case():
    # [x] (x x) = S ([x]x) ([x]x) = S I I
    result = bracket_abstract("x", apply(Atom("x"), Atom("x")))
    assert pretty(result) == "S I I"


def test_expand_bird_derives_not_hardcodes(env):
    # B's SKI form is *derived*; check it's actually a nontrivial S/K/I
    # term (not e.g. literally "B" unchanged), and that expanding twice
    # gives the same (memoized) result.
    ski1 = expand(Atom("B"), env)
    ski2 = expand(Atom("B"), env)
    assert pretty(ski1) == pretty(ski2)
    assert free_vars(ski1) <= {"S", "K", "I"}


def test_expand_leaves_free_variables_untouched(env):
    result = expand(_e("▲ K"), env)
    # ▲ passes through untouched; K gets expanded to bare "K" (already basis)
    assert pretty(result) == "▲ K"


def test_expand_does_not_reduce():
    env = Environment()
    # %ski Q1 x should NOT reduce -- expand only substitutes basis forms.
    result = expand(_e("Q1 x"), env)
    assert "x" in {a for a in free_vars(result)}
    # the result should still literally contain the unreduced application
    # to x at the tail (expand walks structurally, doesn't contract)
    assert pretty(result).endswith("x")


def test_sk_target_has_no_bare_i():
    env = Environment()
    result = expand_sk(_e("Q1"), env)
    assert "I" not in free_vars(result)
    assert free_vars(result) <= {"S", "K"}


def test_expand_bare_combinator_gives_ski_form():
    # "%ski Name" on a bare combinator doubles as "show me the SKI form".
    env = Environment()
    result = expand(Atom("Q1"), env)
    frees = _fresh(3)
    lhs = apply(Atom("Q1"), *frees)
    rhs = apply(result, *frees)
    r1 = reduce(lhs, env, max_steps=100)
    r2 = reduce(rhs, env, max_steps=100)
    assert pretty(r1.term) == pretty(r2.term)


def _fresh(n):
    return [Atom(f"v{i}") for i in range(n)]


# --- user definitions & recursion (SPEC.md §7, §8) --------------------------


def test_user_rule_expands_via_same_mechanism(env):
    env.define_rule("green", ("x", "y", "z"), _e("x (z y)"))
    ski = expand(Atom("green"), env)
    frees = _fresh(3)
    lhs = apply(Atom("green"), *frees)
    rhs = apply(ski, *frees)
    r1 = reduce(lhs, env, max_steps=100)
    r2 = reduce(rhs, env, max_steps=100)
    assert pretty(r1.term) == pretty(r2.term)


def test_user_alias_expands(env):
    env.define_alias("MyAlias", _e("K I"))
    ski = expand(Atom("MyAlias"), env)
    r1 = reduce(_e("MyAlias x y"), env, max_steps=50)
    r2 = reduce(apply(ski, Atom("x"), Atom("y")), env, max_steps=50)
    assert pretty(r1.term) == pretty(r2.term)


def test_recursive_user_definition_reduces_but_cannot_expand(env):
    # 🔁 x -> x (🔁 x): reduces fine (like Y), but %ski must error.
    env.define_rule("🔁", ("x",), _e("x (🔁 x)"))
    res = reduce(_e("🔁 f"), env, max_steps=1, whnf_only=True)
    assert pretty(res.term) == "f (🔁 f)"
    with pytest.raises(ExpansionError):
        expand(Atom("🔁"), env)


def test_recursive_expansion_error_message_names_the_combinator(env):
    env.define_rule("🔁", ("x",), _e("x (🔁 x)"))
    with pytest.raises(ExpansionError, match="🔁"):
        expand(Atom("🔁"), env)


def test_builtin_y_expands_fine_despite_recursive_rule(env):
    # Y's *rule* is self-referential, but it carries an explicit ski
    # override, so expansion succeeds where a user-typed sage would fail.
    result = expand(Atom("Y"), env)
    assert free_vars(result) <= {"S", "K", "I"}


def test_theta_expands_finitely(env):
    # Θ := U U is not *textually* self-referential (U's own rule doesn't
    # mention Θ), so it should expand to a finite SKI term even though it
    # behaves as a fixed-point combinator under reduction.
    result = expand(Atom("Θ"), env)
    assert free_vars(result) <= {"S", "K", "I"}
