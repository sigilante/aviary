"""AviaryKernel: the Jupyter protocol surface (SPEC.md §10)."""

from __future__ import annotations

from ipykernel.kernelbase import Kernel

from .abstraction import ExpansionError
from .birds import BIRDS, BY_NAME
from .environment import Environment, DefinitionError
from .magics import dispatch as dispatch_magic, MagicError, AVAILABLE_MAGICS, Output, card_for_bird, card_for_definition
from .parser import (
    parse_cell, ParseError, Magic, Alias, Rule, Expr,
    paren_balance, canonicalize,
)
from .reduce import reduce, Status, InterruptFlag
from .terms import size as term_size

__version__ = "0.1.0"


def _status_warning(status: Status, steps: int, size: int, max_size: int) -> str | None:
    if status == Status.FUEL:
        return f"⚠ no normal form after {steps} steps (fuel exhausted); term size {size}"
    if status == Status.SIZE:
        return f"⚠ term exceeded {max_size} atoms after {steps} steps"
    if status == Status.INTERRUPTED:
        return f"⚠ interrupted after {steps} steps; partial term shown"
    return None


class AviaryKernel(Kernel):
    implementation = "aviary"
    implementation_version = __version__
    language = "combinatory-logic"
    language_version = "1.0"
    language_info = {
        "name": "combinatory-logic",
        "file_extension": ".cl",
        "mimetype": "text/x-combinatory-logic",
        "pygments_lexer": "text",
    }
    banner = "Aviary -- a combinator-calculus kernel. Try: K ▲ (M M)"
    help_links = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.env = Environment()
        self._interrupt_flag = InterruptFlag()

    # --- execution ------------------------------------------------------

    async def do_execute(self, code, silent, store_history=True,
                          user_expressions=None, allow_stdin=False,
                          *, cell_meta=None, cell_id=None):
        self._interrupt_flag.clear()
        try:
            stmts = parse_cell(code)
        except ParseError as e:
            return self._error_reply("ParseError", e.message, str(e))

        last_expr_idx = None
        for i, s in enumerate(stmts):
            if isinstance(s, Expr):
                last_expr_idx = i

        for i, stmt in enumerate(stmts):
            try:
                if isinstance(stmt, Magic):
                    outputs = dispatch_magic(stmt, self.env)
                    if not silent:
                        for o in outputs:
                            self._emit(o)
                elif isinstance(stmt, Alias):
                    self._handle_alias(stmt, silent)
                elif isinstance(stmt, Rule):
                    self._handle_rule(stmt, silent)
                elif isinstance(stmt, Expr):
                    self._handle_expr(stmt, is_last=(i == last_expr_idx), silent=silent)
            except DefinitionError as e:
                return self._error_reply("DefinitionError", str(e), str(e))
            except ExpansionError as e:
                return self._error_reply("ExpansionError", str(e), str(e))
            except MagicError as e:
                return self._error_reply("MagicError", str(e), str(e))
            except KeyboardInterrupt:
                if not silent:
                    self._stream("stderr", "⚠ interrupted; partial results shown")
                break

        return {
            "status": "ok",
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }

    def _handle_alias(self, stmt: Alias, silent: bool) -> None:
        name = stmt.name_token.canonical
        self.env.define_alias(name, stmt.expr, source_text="")
        if not silent:
            self._stream("stdout", f"defined {name} := {self.env.pretty(stmt.expr)}")

    def _handle_rule(self, stmt: Rule, silent: bool) -> None:
        name = stmt.name_token.canonical
        formals = tuple(t.canonical for t in stmt.var_tokens)
        d = self.env.define_rule(name, formals, stmt.expr, source_text="")
        if not silent:
            rule_str = f"{name} {' '.join(formals)} -> {self.env.pretty(stmt.expr)}"
            self._stream("stdout", f"defined {name} (arity {len(formals)}): {rule_str}")
            free_syms = getattr(d, "_free_syms", set())
            if free_syms:
                self._stream("stdout", f"note: free symbol(s) in body: {', '.join(sorted(free_syms))}")

    def _handle_expr(self, stmt: Expr, is_last: bool, silent: bool) -> None:
        res = reduce(stmt.expr, self.env, interrupt=self._interrupt_flag)
        text = self.env.pretty(res.term)
        if res.status == Status.NORMAL and res.steps == 0:
            suffix = "  [normal form]"
        else:
            suffix = f"  [{res.steps} step{'s' if res.steps != 1 else ''}]"
        rendered = text + suffix
        if not silent:
            data = {"text/plain": rendered}
            if is_last:
                self.send_response(self.iopub_socket, "execute_result", {
                    "execution_count": self.execution_count,
                    "data": data,
                    "metadata": {},
                })
            else:
                self.send_response(self.iopub_socket, "display_data", {
                    "data": data,
                    "metadata": {},
                })
            warning = _status_warning(res.status, res.steps, term_size(res.term), self.env.max_size)
            if warning:
                self._stream("stderr", warning)

    def _emit(self, o: Output) -> None:
        if o.kind == "stream":
            self._stream(o.stream_name, o.text)
        elif o.kind == "display_data":
            self.send_response(self.iopub_socket, "display_data", {"data": o.data, "metadata": {}})
        elif o.kind == "execute_result":
            self.send_response(self.iopub_socket, "execute_result", {
                "execution_count": self.execution_count,
                "data": o.data,
                "metadata": {},
            })

    def _stream(self, name: str, text: str) -> None:
        self.send_response(self.iopub_socket, "stream", {"name": name, "text": text + "\n"})

    def _error_reply(self, ename: str, message: str, traceback_line: str) -> dict:
        self.send_response(self.iopub_socket, "error", {
            "ename": ename, "evalue": message, "traceback": [traceback_line],
        })
        return {
            "status": "error",
            "execution_count": self.execution_count,
            "ename": ename,
            "evalue": message,
            "traceback": [traceback_line],
        }

    # --- interrupt --------------------------------------------------------

    def do_interrupt(self):
        self._interrupt_flag.set()

    # --- completion / inspection -----------------------------------------

    def _completion_candidates(self) -> list[str]:
        cands: set[str] = set()
        for b in BIRDS:
            cands.add(b.name)
            cands.add(b.display)
            cands.update(b.aliases)
        for d in self.env.user_definitions():
            cands.add(d.name)
        cands.add("Θ")  # Theta
        cands.add("Theta")
        return sorted(cands)

    async def do_complete(self, code, cursor_pos):
        line_start = code.rfind("\n", 0, cursor_pos) + 1
        line = code[line_start:cursor_pos]
        start = len(line)
        while start > 0 and line[start - 1] not in " \t()":
            start -= 1
        prefix = line[start:]
        cursor_start = line_start + start

        if line.lstrip().startswith("%") and prefix.startswith("%"):
            matches = [m for m in AVAILABLE_MAGICS if m.startswith(prefix)]
        else:
            matches = [c for c in self._completion_candidates() if c.startswith(prefix)] if prefix else []

        return {
            "matches": matches,
            "cursor_start": cursor_start,
            "cursor_end": cursor_pos,
            "metadata": {},
            "status": "ok",
        }

    async def do_inspect(self, code, cursor_pos, detail_level=0, omit_sections=()):
        line_start = code.rfind("\n", 0, cursor_pos) + 1
        line_end = code.find("\n", cursor_pos)
        if line_end == -1:
            line_end = len(code)
        line = code[line_start:line_end]
        rel = cursor_pos - line_start
        start = rel
        while start > 0 and line[start - 1] not in " \t()":
            start -= 1
        end = rel
        while end < len(line) and line[end] not in " \t()":
            end += 1
        token = canonicalize(line[start:end])
        if not token:
            return {"status": "ok", "data": {}, "metadata": {}, "found": False}

        b = BY_NAME.get(token)
        if b is not None:
            card = card_for_bird(b, self.env)
            return {"status": "ok", "data": {"text/plain": card}, "metadata": {}, "found": True}
        canon = self.env._alias_keys.get(token, token)
        d = self.env.definitions.get(canon)
        if d is not None:
            card = card_for_definition(d, self.env)
            return {"status": "ok", "data": {"text/plain": card}, "metadata": {}, "found": True}
        return {"status": "ok", "data": {}, "metadata": {}, "found": False}

    async def do_is_complete(self, code):
        last_line = code.split("\n")[-1] if code else ""
        if paren_balance(code) > 0:
            return {"status": "incomplete", "indent": ""}
        return {"status": "complete"}
