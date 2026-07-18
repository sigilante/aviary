"""%-command dispatch (SPEC.md §9)."""

from __future__ import annotations

from dataclasses import dataclass, field

from .abstraction import expand, expand_sk, ExpansionError
from .birds import BIRDS, BY_NAME
from .environment import Environment, DefinitionError
from .parser import Magic, parse_expr_tokens, canonicalize
from .reduce import reduce, Status, TraceStep
from .terms import Atom, pretty as _pretty


class MagicError(Exception):
    pass


AVAILABLE_MAGICS = (
    "%trace", "%whnf", "%ski", "%sk", "%fuel", "%size",
    "%birds", "%whatis", "%defs", "%undef", "%ascii",
)


@dataclass
class Output:
    kind: str  # 'execute_result' | 'display_data' | 'stream' | 'error'
    data: dict | None = None
    stream_name: str | None = None
    text: str | None = None
    ename: str | None = None
    evalue: str | None = None


def _stream(name: str, text: str) -> Output:
    return Output(kind="stream", stream_name=name, text=text)


def _display(plain: str, markdown: str | None = None) -> Output:
    data = {"text/plain": plain}
    if markdown is not None:
        data["text/markdown"] = markdown
    return Output(kind="display_data", data=data)


def _one_atom_arg(magic: Magic) -> str:
    toks = [t for t in magic.arg_tokens if t.kind == "atom"]
    if len(magic.arg_tokens) != 1 or not toks:
        raise MagicError(f"{magic.name} expects a single name argument")
    return magic.arg_tokens[0].canonical


def _parse_arg_expr(magic: Magic):
    if not magic.arg_tokens:
        raise MagicError(f"{magic.name} expects an expression argument")
    return parse_expr_tokens(magic.arg_tokens, magic.line)


def _trace_line(step: int, contracted: str | None, term_str: str) -> str:
    label = contracted or ""
    return f"{label:<4}{step:>4}  {term_str}"


def _format_trace(trace: list[TraceStep], env: Environment, elide: bool) -> str:
    lines = [_trace_line(t.step, t.contracted, env.pretty(t.term)) for t in trace]
    if elide and len(lines) > 200:
        head = lines[:100]
        tail = lines[-100:]
        elided = len(lines) - 200
        return "\n".join(head + [f"    … {elided} steps elided …"] + tail)
    return "\n".join(lines)


def card_for_bird(b, env: Environment) -> str:
    names = "/".join(sorted({b.name, b.display, *b.aliases}))
    formals = list(b.formals)
    lam = f"λ{' '.join(formals)}. {env.pretty(b.rule)}"
    rule_line = f"{env.display_name(b.name)} {' '.join(formals)} = {env.pretty(b.rule)}"
    try:
        ski = env.pretty(expand(Atom(b.name), env))
    except ExpansionError as e:
        ski = f"(unexpandable: {e})"
    return (
        f"{names} -- {b.bird_name} (arity {b.arity})\n"
        f"  rule:  {rule_line}\n"
        f"  λ:     {lam}\n"
        f"  S/K/I: {ski}"
    )


def card_for_definition(d, env: Environment) -> str:
    if d.is_alias:
        rule_line = f"{d.name} := {env.pretty(d.body)}"
        lam = env.pretty(d.body)
    else:
        rule_line = f"{d.name} {' '.join(d.formals)} -> {env.pretty(d.body)}"
        lam = f"λ{' '.join(d.formals)}. {env.pretty(d.body)}"
    try:
        ski = env.pretty(expand(Atom(d.name), env))
    except ExpansionError as e:
        ski = f"(unexpandable: {e})"
    kind = "built-in alias" if d.builtin else ("user alias" if d.is_alias else "user rule")
    return (
        f"{d.name} -- {kind} (arity {d.arity})\n"
        f"  rule:  {rule_line}\n"
        f"  λ:     {lam}\n"
        f"  S/K/I: {ski}"
    )


def dispatch(magic: Magic, env: Environment) -> list[Output]:
    name = magic.name

    if name == "%trace":
        expr = _parse_arg_expr(magic)
        res = reduce(expr, env, trace=True)
        elide = not env.fuel_changed
        text = _format_trace(res.trace, env, elide)
        outputs = [_stream("stdout", text)]
        if res.status == Status.FUEL:
            outputs.append(_stream("stderr",
                f"⚠ no normal form after {res.steps} steps (fuel exhausted); "
                f"term size {_term_size(res.term)}"))
        elif res.status == Status.SIZE:
            outputs.append(_stream("stderr",
                f"⚠ term exceeded {env.max_size} atoms after {res.steps} steps"))
        elif res.status == Status.INTERRUPTED:
            outputs.append(_stream("stderr", "⚠ interrupted; partial term shown"))
        return outputs

    if name == "%whnf":
        expr = _parse_arg_expr(magic)
        res = reduce(expr, env, whnf_only=True)
        return [_finish_reduction(res, env)]

    if name in ("%ski", "%sk"):
        expr = _parse_arg_expr(magic)
        try:
            result = expand(expr, env) if name == "%ski" else expand_sk(expr, env)
        except ExpansionError as e:
            raise MagicError(str(e)) from e
        return [_display(env.pretty(result))]

    if name == "%fuel":
        if not magic.arg_tokens:
            return [_stream("stdout", f"fuel (max_steps) = {env.max_steps}")]
        raw = _one_atom_arg(magic)
        try:
            n = int(raw)
            if n <= 0:
                raise ValueError
        except ValueError:
            raise MagicError(f"%fuel expects a positive integer, got '{raw}'")
        env.max_steps = n
        env.fuel_changed = n != 10_000
        return [_stream("stdout", f"fuel (max_steps) set to {n}")]

    if name == "%size":
        if not magic.arg_tokens:
            return [_stream("stdout", f"size (max_size) = {env.max_size}")]
        raw = _one_atom_arg(magic)
        try:
            n = int(raw)
            if n <= 0:
                raise ValueError
        except ValueError:
            raise MagicError(f"%size expects a positive integer, got '{raw}'")
        env.max_size = n
        env.size_changed = n != 100_000
        return [_stream("stdout", f"size (max_size) set to {n}")]

    if name == "%birds":
        rows = sorted(BIRDS, key=lambda b: b.name)
        plain_lines = [f"{b.name:<6}{b.bird_name:<28}{b.arity:<3}{env.pretty(b.rule)}" for b in rows]
        plain = "\n".join(["NAME   BIRD                        AR  RULE"] + plain_lines)
        md_lines = ["| Name | Bird | Arity | Rule |", "|---|---|---|---|"]
        for b in rows:
            md_lines.append(f"| `{env.display_name(b.name)}` | {b.bird_name} | {b.arity} | `{env.pretty(b.rule)}` |")
        return [_display(plain, "\n".join(md_lines))]

    if name == "%whatis":
        target = _one_atom_arg(magic)
        b = BY_NAME.get(target)
        if b is not None:
            return [_display(card_for_bird(b, env))]
        canon = env._alias_keys.get(target, target)
        d = env.definitions.get(canon)
        if d is not None:
            return [_display(card_for_definition(d, env))]
        raise MagicError(f"unknown name '{target}'")

    if name == "%defs":
        defs = env.user_definitions()
        if not defs:
            return [_stream("stdout", "(no user definitions)")]
        lines = []
        for d in defs:
            if d.is_alias:
                lines.append(f"{d.name} := {env.pretty(d.body)}")
            else:
                lines.append(f"{d.name} {' '.join(d.formals)} -> {env.pretty(d.body)}  (arity {d.arity})")
        return [_stream("stdout", "\n".join(lines))]

    if name == "%undef":
        target = _one_atom_arg(magic)
        try:
            env.undef(target)
        except DefinitionError as e:
            raise MagicError(str(e)) from e
        return [_stream("stdout", f"undefined {target}")]

    if name == "%ascii":
        arg = _one_atom_arg(magic)
        if arg == "on":
            env.ascii_mode = True
        elif arg == "off":
            env.ascii_mode = False
        else:
            raise MagicError("%ascii expects 'on' or 'off'")
        return [_stream("stdout", f"ascii mode {'on' if env.ascii_mode else 'off'}")]

    raise MagicError(f"unknown magic '{name}'; available: {', '.join(AVAILABLE_MAGICS)}")


def _term_size(term) -> int:
    from .terms import size
    return size(term)


def _finish_reduction(res, env: Environment) -> Output:
    text = env.pretty(res.term)
    if res.status == Status.NORMAL and res.steps == 0:
        suffix = "  [normal form]"
    elif res.status == Status.NORMAL:
        suffix = f"  [{res.steps} step{'s' if res.steps != 1 else ''}]"
    elif res.status == Status.WHNF:
        suffix = f"  [whnf, {res.steps} step{'s' if res.steps != 1 else ''}]"
    else:
        suffix = f"  [{res.steps} steps]"
    out = Output(kind="execute_result", data={"text/plain": text + suffix})
    return out
