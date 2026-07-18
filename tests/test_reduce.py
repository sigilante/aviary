"""SPEC.md §12 items 4 (laziness), 5 (normal order to NF), 6 (Y), 8
(fuel/size/interrupt)."""

from __future__ import annotations

import pytest

from aviary_kernel.environment import Environment
from aviary_kernel.parser import parse_cell
from aviary_kernel.reduce import reduce, whnf, Status, InterruptFlag
from aviary_kernel.terms import pretty


def _e(src: str):
    return parse_cell(src)[0].expr


# --- §12 item 4: laziness --------------------------------------------------


def test_laziness_k_discards_second_arg(env):
    res = reduce(_e("K ▲ (M M)"), env)
    assert pretty(res.term) == "▲"
    assert res.steps == 1
    assert res.status == Status.NORMAL


def test_laziness_kite_discards_first_arg(env):
    res = reduce(_e("Ki (M M) ▲"), env)
    assert pretty(res.term) == "▲"
    assert res.steps == 1
    assert res.status == Status.NORMAL


def test_laziness_skk_terminates(env):
    res = reduce(_e("S K (M M) ▲"), env, max_steps=1000)
    assert res.status == Status.NORMAL
    assert pretty(res.term) == "▲"


def test_m_m_alone_exhausts_fuel_gracefully(env):
    res = reduce(_e("M M"), env, max_steps=500)
    assert res.status == Status.FUEL
    assert res.steps == 500
    # not an error -- just a (non-growing, in this case) partial term
    assert pretty(res.term) == "M M"


# --- §12 item 5: normal order to full normal form --------------------------


def test_normal_order_normalizes_stuck_arguments(env):
    # B ▲ 🟢 (K ◆ ●) => ▲ (🟢 ◆): head sticks on the free var ▲, then both
    # arguments are normalized left-to-right.
    res = reduce(_e("B ▲ 🟢 (K ◆ ●)"), env)
    assert pretty(res.term) == "▲ (🟢 ◆)"
    assert res.status == Status.NORMAL


def test_normal_order_does_not_evaluate_discarded_arg_deeply():
    env = Environment()
    res = reduce(_e("K x (M M)"), env, max_steps=5)
    assert pretty(res.term) == "x"
    assert res.status == Status.NORMAL
    assert res.steps == 1


# --- §12 item 6: Y ----------------------------------------------------------


def test_y_f_unfolds_in_one_step(env):
    res = reduce(_e("Y f"), env, max_steps=1, whnf_only=True)
    assert res.steps == 1
    assert pretty(res.term) == "f (Y f)"


def test_y_f_trace_first_step():
    env = Environment()
    res = reduce(_e("Y f"), env, max_steps=3, trace=True)
    assert res.trace[0].term == _e("Y f")
    assert res.trace[0].contracted is None
    assert res.trace[1].contracted == "Y"
    assert pretty(res.trace[1].term) == "f (Y f)"


# --- §12 item 8: fuel / size / interrupt -----------------------------------


def test_fuel_exhaustion_is_not_an_error_status(env):
    res = reduce(_e("Y f"), env, max_steps=100)
    assert res.status == Status.FUEL
    assert res.steps == 100
    # partial term still printable
    assert isinstance(pretty(res.term), str)


def test_size_exhaustion():
    env = Environment()
    # M (M (K ▲)) style growth via repeated self-application; use a small
    # size cap so we hit SIZE before FUEL.
    res = reduce(_e("Y M"), env, max_steps=1000, max_size=50)
    assert res.status == Status.SIZE


def test_interrupt_mid_reduction_leaves_reducer_usable():
    env = Environment()
    flag = InterruptFlag()
    flag.set()
    res = reduce(_e("M M"), env, max_steps=1000, interrupt=flag)
    assert res.status == Status.INTERRUPTED
    assert res.steps == 0
    # reducer is still usable for a fresh call afterward
    flag2 = InterruptFlag()
    res2 = reduce(_e("K ▲ (M M)"), env, interrupt=flag2)
    assert res2.status == Status.NORMAL
    assert pretty(res2.term) == "▲"


def test_interrupt_after_n_steps():
    # The interrupt flag is polled before every contraction *attempt*,
    # including the final check that discovers WHNF has been reached (so
    # is_set() is called more often than there are successful
    # contractions) -- we only assert the coarser, spec-mandated
    # invariants: it aborts promptly (well under max_steps) and reports
    # a consistent, non-error, partial result.
    env = Environment()

    class CountingFlag:
        def __init__(self, n):
            self.count = 0
            self.n = n

        def is_set(self):
            self.count += 1
            return self.count > self.n

    cf = CountingFlag(5)
    res = reduce(_e("Y f"), env, max_steps=1000, interrupt=cf)
    assert res.status == Status.INTERRUPTED
    assert 0 < res.steps <= 5


# --- whnf-only mode ----------------------------------------------------------


def test_whnf_stops_before_normalizing_args(env):
    # ▲ is free, so the term is already stuck at the head -- whnf() should
    # return it completely unchanged, in particular *without* descending
    # into (K ◆ ●) the way full normalization would.
    res = whnf(_e("▲ 🟢 (K ◆ ●)"), env)
    assert res.status == Status.WHNF
    assert res.steps == 0
    assert pretty(res.term) == "▲ 🟢 (K ◆ ●)"


def test_whnf_contracts_head_but_not_stuck_arguments(env):
    # B fires (head redex), but the resulting stuck argument (K ◆ ●)
    # must NOT be normalized under whnf_only -- that's the §6.1 step 4
    # boundary whnf_only stops before.
    res = whnf(_e("B ▲ 🟢 (K ◆ ●)"), env)
    assert res.status == Status.WHNF
    assert res.steps == 1
    assert pretty(res.term) == "▲ (🟢 (K ◆ ●))"


def test_whnf_still_contracts_head_redexes(env):
    res = whnf(_e("K ▲ (M M)"), env)
    assert res.status == Status.WHNF
    assert pretty(res.term) == "▲"
