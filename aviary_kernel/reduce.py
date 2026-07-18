"""Normal-order (leftmost-outermost) reduction to full normal form
(SPEC.md §6).

The reducer is a single iterative state machine -- it uses an explicit
Python list as a stack instead of recursive function calls -- because
deep spines and deep argument-nesting (both common once you start
contracting Y-chains or towers of B/S combinators) would otherwise blow
Python's recursion limit (SPEC.md §10). Fuel (step count) is checked
*before* every contraction wherever it occurs in the term; size is
checked *after* every contraction (so the reported "exceeded" term is
the one that tipped it over); an interrupt flag is checked at the same
point as fuel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .environment import Environment, Combinator
from .terms import Atom, App, Term, apply, size as term_size, substitute


class InterruptFlag:
    """A simple mutable flag do_interrupt() can set; polled by the reducer
    between contractions (SPEC.md §10)."""

    def __init__(self) -> None:
        self._flag = False

    def set(self) -> None:
        self._flag = True

    def clear(self) -> None:
        self._flag = False

    def is_set(self) -> bool:
        return self._flag


class Status(Enum):
    NORMAL = "normal"              # ran to full normal form
    WHNF = "whnf"                   # stopped at weak head normal form (on request)
    FUEL = "fuel"                    # exhausted max_steps
    SIZE = "size"                    # exceeded max_size
    INTERRUPTED = "interrupted"


@dataclass
class ReduceResult:
    term: Term
    steps: int
    status: Status
    trace: list["TraceStep"] = field(default_factory=list)


@dataclass
class TraceStep:
    step: int
    term: Term
    contracted: Optional[str]  # combinator contracted to reach this term; None for step 0


def _decompose(term: Term) -> tuple[Atom, list[Term]]:
    args: list[Term] = []
    cur = term
    while isinstance(cur, App):
        args.append(cur.arg)
        cur = cur.fn
    args.reverse()
    assert isinstance(cur, Atom)
    return cur, args


def _try_contract(head: Atom, args: list[Term], env: Environment) -> tuple[Atom, list[Term], str] | None:
    """If (head, args) is a redex, contract it (§6.1). Only the first
    `arity` args are consumed; extras stay applied to the result."""
    comb = env.lookup(head.name)
    if comb is None:
        return None
    if len(args) < comb.arity:
        return None
    consumed = args[: comb.arity]
    rest = args[comb.arity:]
    mapping = dict(zip(comb.formals, consumed))
    new_term = substitute(comb.body, mapping)
    new_head, new_args_from_body = _decompose(new_term)
    return new_head, new_args_from_body + rest, comb.name


@dataclass
class _Frame:
    head: Atom
    done: list[Term]
    todo: list[Term]


def reduce(term: Term, env: Environment, *, whnf_only: bool = False,
           max_steps: Optional[int] = None, max_size: Optional[int] = None,
           interrupt: Optional[InterruptFlag] = None,
           trace: bool = False, trace_limit: int = 200) -> ReduceResult:
    """Reduce ``term`` under normal order to full normal form (or to WHNF
    if ``whnf_only``)."""
    limit_steps = max_steps if max_steps is not None else env.max_steps
    limit_size = max_size if max_size is not None else env.max_size
    steps = 0
    trace_steps: list[TraceStep] = []
    if trace:
        trace_steps.append(TraceStep(step=0, term=term, contracted=None))

    stack: list[_Frame] = []

    def full_term(head: Atom, args: list[Term]) -> Term:
        result: Term = apply(head, *args)
        for fr in reversed(stack):
            remaining = fr.todo[len(fr.done) + 1:]
            result = apply(fr.head, *(fr.done + [result] + remaining))
        return result

    head, args = _decompose(term)

    def record(status: Status) -> ReduceResult:
        return ReduceResult(full_term(head, args), steps, status, trace_steps)

    while True:
        # --- bring `head`/`args` (the current position) to WHNF ---------
        while True:
            if interrupt is not None and interrupt.is_set():
                return record(Status.INTERRUPTED)
            if steps >= limit_steps:
                return record(Status.FUEL)
            contraction = _try_contract(head, args, env)
            if contraction is None:
                break
            head, args, name = contraction
            steps += 1
            if term_size(full_term(head, args)) > limit_size:
                res = record(Status.SIZE)
                if trace:
                    trace_steps.append(TraceStep(step=steps, term=res.term, contracted=name))
                return res
            if trace:
                trace_steps.append(TraceStep(step=steps, term=full_term(head, args), contracted=name))

        if whnf_only and not stack:
            return ReduceResult(apply(head, *args), steps, Status.WHNF, trace_steps)

        if args:
            stack.append(_Frame(head=head, done=[], todo=list(args)))
            head, args = _decompose(args[0])
            continue

        # `head` (with no args) is fully normal at this position.
        result: Term = head
        while stack:
            fr = stack[-1]
            fr.done.append(result)
            remaining = fr.todo[len(fr.done):]
            if remaining:
                head, args = _decompose(remaining[0])
                break
            built = apply(fr.head, *fr.done)
            stack.pop()
            result = built
        else:
            return ReduceResult(result, steps, Status.NORMAL, trace_steps)
        # loop back to bring the new head/args (from `remaining[0]`) to WHNF


def whnf(term: Term, env: Environment, **kwargs) -> ReduceResult:
    return reduce(term, env, whnf_only=True, **kwargs)
