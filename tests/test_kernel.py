"""SPEC.md §12 item 9 (kernel end-to-end via jupyter_client) and item 7
(definitions, exercised both directly on Environment -- for the
constraint-checking details -- and through the real kernel protocol).
"""

from __future__ import annotations

import os
import sys

import pytest

from aviary_kernel.environment import Environment, DefinitionError
from aviary_kernel.parser import parse_cell


def _e(src: str):
    return parse_cell(src)[0].expr


# --- §12 item 7: definitions (fast, direct on Environment) -----------------


def test_rule_definition_reduces_and_ski_expands(env):
    from aviary_kernel.abstraction import expand
    from aviary_kernel.reduce import reduce
    from aviary_kernel.terms import pretty, apply, Atom

    env.define_rule("🟢", ("x", "y", "z"), _e("x (z y)"))
    res = reduce(_e("🟢 a b c"), env, max_steps=10)
    assert pretty(res.term) == "a (c b)"
    ski = expand(Atom("🟢"), env)
    from aviary_kernel.terms import free_vars
    assert free_vars(ski) <= {"S", "K", "I"}
    assert len(pretty(ski)) > 0


def test_alias_stays_folded_when_unused(env):
    from aviary_kernel.reduce import reduce
    from aviary_kernel.terms import pretty

    env.define_alias("MyAlias", _e("some_undefined_thing_that_would_blow_up"))
    res = reduce(_e("K ▲ MyAlias"), env, max_steps=10)
    assert pretty(res.term) == "▲"
    assert res.steps == 1  # only the K-redex; MyAlias never touched


def test_recursive_user_definition_reduces_but_ski_errors(env):
    from aviary_kernel.abstraction import expand, ExpansionError
    from aviary_kernel.reduce import reduce
    from aviary_kernel.terms import pretty, Atom

    env.define_rule("🔁", ("x",), _e("x (🔁 x)"))
    res = reduce(_e("🔁 f"), env, max_steps=1, whnf_only=True)
    assert pretty(res.term) == "f (🔁 f)"
    with pytest.raises(ExpansionError):
        expand(Atom("🔁"), env)


def test_shadowing_builtin_is_error(env):
    with pytest.raises(DefinitionError, match="shadow"):
        env.define_alias("K", _e("I"))
    with pytest.raises(DefinitionError, match="shadow"):
        env.define_rule("B", ("x", "y"), _e("x y"))


def test_shadowing_theta_is_error(env):
    with pytest.raises(DefinitionError, match="shadow"):
        env.define_alias("Θ", _e("I"))


def test_rule_variable_shadowing_combinator_is_error(env):
    with pytest.raises(DefinitionError, match="shadows a combinator"):
        env.define_rule("foo", ("K",), _e("K K"))


def test_rule_duplicate_variable_is_error(env):
    with pytest.raises(DefinitionError, match="duplicate"):
        env.define_rule("foo", ("x", "x"), _e("x x"))


def test_redefining_user_definition_replaces_it(env):
    env.define_alias("A", _e("I"))
    env.define_alias("A", _e("K"))
    assert env.definitions["A"].body == _e("K")


def test_undef_removes_user_definition(env):
    env.define_alias("A", _e("I"))
    env.undef("A")
    assert "A" not in env.definitions
    with pytest.raises(DefinitionError):
        env.undef("A")


def test_undef_builtin_is_error(env):
    with pytest.raises(DefinitionError):
        env.undef("Θ")


# --- §12 item 9: kernel end-to-end (jupyter_client) -------------------------


def _has_ipc_support():
    try:
        import jupyter_client  # noqa
        return True
    except ImportError:
        return False


@pytest.fixture(scope="module")
def kernel_client():
    from jupyter_client.manager import KernelManager

    km = KernelManager(kernel_name="aviary")
    km.start_kernel(
        extra_arguments=[],
    )
    kc = km.client()
    kc.start_channels()
    kc.wait_for_ready(timeout=60)
    yield kc
    kc.stop_channels()
    km.shutdown_kernel(now=True)


def _run(kc, code, timeout=15):
    msg_id = kc.execute(code)
    outputs = []
    while True:
        msg = kc.get_iopub_msg(timeout=timeout)
        if msg["parent_header"].get("msg_id") != msg_id:
            continue
        mt = msg["msg_type"]
        if mt == "status" and msg["content"]["execution_state"] == "idle":
            break
        outputs.append((mt, msg["content"]))
    while True:
        reply = kc.get_shell_msg(timeout=timeout)
        if reply["parent_header"].get("msg_id") == msg_id:
            return outputs, reply["content"]


def _shell(kc, method, *args, timeout=15):
    msg_id = getattr(kc, method)(*args)
    while True:
        reply = kc.get_shell_msg(timeout=timeout)
        if reply["parent_header"].get("msg_id") == msg_id:
            return reply["content"]


@pytest.mark.skipif(sys.platform == "win32", reason="kernel process launch flaky on CI Windows")
def test_execute_request_returns_execute_result(kernel_client):
    outputs, reply = _run(kernel_client, "K ▲ (M M)")
    assert reply["status"] == "ok"
    results = [c for mt, c in outputs if mt == "execute_result"]
    assert len(results) == 1
    assert results[0]["data"]["text/plain"].startswith("▲")


def test_multi_statement_cell_last_expr_is_execute_result(kernel_client):
    outputs, reply = _run(kernel_client, "K x y\nS K K")
    assert reply["status"] == "ok"
    kinds = [mt for mt, c in outputs]
    assert kinds.count("execute_result") == 1
    assert kinds.count("display_data") == 1


def test_completion_offers_unicode_subscript_form(kernel_client):
    reply = _shell(kernel_client, "complete", "Q", 1)
    assert "Q₁" in reply["matches"]
    assert "Q1" in reply["matches"]


def test_is_complete_unclosed_paren(kernel_client):
    reply = _shell(kernel_client, "is_complete", "B (S")
    assert reply["status"] == "incomplete"


def test_is_complete_balanced(kernel_client):
    reply = _shell(kernel_client, "is_complete", "B (S K)")
    assert reply["status"] == "complete"


def test_parse_error_is_error_reply(kernel_client):
    outputs, reply = _run(kernel_client, "K (x y")
    assert reply["status"] == "error"
    assert reply["ename"] == "ParseError"


def test_fuel_exhaustion_is_ok_status_with_warning(kernel_client):
    outputs, reply = _run(kernel_client, "%fuel 50\nM M\n%fuel 10000")
    assert reply["status"] == "ok"
    warnings = [c for mt, c in outputs if mt == "stream" and c.get("name") == "stderr"]
    assert any("fuel exhausted" in c["text"] for c in warnings)


def test_definition_and_use_end_to_end(kernel_client):
    outputs, reply = _run(kernel_client, "🟡 x y z -> x (z y)\nK 🟡 ▲")
    assert reply["status"] == "ok"
    stream_texts = [c["text"] for mt, c in outputs if mt == "stream"]
    assert any("defined 🟡" in t for t in stream_texts)


def test_ascii_magic_toggles_display(kernel_client):
    outputs, reply = _run(kernel_client, "%ascii on")
    assert reply["status"] == "ok"
    outputs2, reply2 = _run(kernel_client, "Q1")
    assert reply2["status"] == "ok"
    result = [c for mt, c in outputs2 if mt == "execute_result"][0]
    assert result["data"]["text/plain"].startswith("Q1")
    # restore default for other tests
    _run(kernel_client, "%ascii off")


def test_ski_magic_end_to_end(kernel_client):
    outputs, reply = _run(kernel_client, "%ski Q1")
    assert reply["status"] == "ok"
    disp = [c for mt, c in outputs if mt == "display_data"][0]
    assert "S" in disp["data"]["text/plain"]


def test_undef_unknown_is_magic_error(kernel_client):
    outputs, reply = _run(kernel_client, "%undef NoSuchName")
    assert reply["status"] == "error"
    assert reply["ename"] == "MagicError"
