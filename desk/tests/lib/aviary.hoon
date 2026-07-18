::::  /tests/lib/aviary -- combinator-suite regression tests, in the
::  standard `-test %` (`/ted/test.hoon`) thread style. Complements
::  tests/test-engine.sh (SPEC-DESK.md §7's added deliverable, once the
::  registry cross-test passes): same engine, exercised the idiomatic
::  desk-test way rather than through a raw `urbit eval` pipe.
::
::  Run on an installed %aviary desk with `-test %/tests/lib/aviary`.
::
/+  *test
/+  *aviary
/-  *aviary
|%
::  +expect-run: run one statement against a fresh session and expect its
::  output lines to equal `out`.
::
++  expect-run
  |=  [line=tape out=(list tape)]
  ^-  tang
  =/  res  (run default-env line)
  (expect-eq !>(out) !>(out.res))
::
::  +test-every-bird-one-step: SPEC.md §5.2's full aviary, each applied to
::  fresh free variables, contracts to exactly its own registry rule.
::
++  test-every-bird-one-step
  ^-  tang
  =|  tan=tang
  =/  bs=(list bird)  birds
  |-
  ^-  tang
  ?~  bs  tan
  =/  ar  arity.i.bs
  =/  formals  (formals-for ar)
  =/  fresh=(list @t)
    (turn (gulf 1 ar) |=(i=@ud (cat 3 'v' (add 48 i))))
  =/  args=(list term)  fresh
  =/  input  (mk-app name.i.bs args)
  =/  got  rt:(reduce default-env input)
  =/  want  (subst (parse-rule-text rule.i.bs) (zip-map formals args))
  ::  a plain noun `=()` here, not expect-eq's !>(...)/~(nest ut ...)
  ::  path -- the latter drags the type-nester over the engine's
  ::  recursive $@-based `term` mold, which this Hoon/vere combination
  ::  cannot always walk (the same +dig limitation as the `%over` this
  ::  file's sibling, lib/aviary.hoon, documents at its header).
  ::
  =/  case-result
    %+  category  (trip name.i.bs)
    (expect !>(=(got want)))
  $(bs t.bs, tan (weld tan case-result))
::
::  +test-laziness: the Mockingbird-fondness laziness litmus test (SPEC.md
::  §1): K discards its second argument without ever reducing it.
::
++  test-laziness
  ^-  tang
  %+  category  "K x (M M)"
  (expect-run "K vvv (M M)" ["vvv  [1 step]"]~)
::
::  +test-full-normalization: normal order continues into arguments once
::  the head is stuck (SPEC.md §6.1 step 4), and Unicode atoms round-trip.
::
++  test-full-normalization
  ^-  tang
  %+  category  "B a b (K c d)"
  (expect-run "B ▲ 🟢 (K ◆ ●)" ["▲ (🟢 ◆)  [2 steps]"]~)
::
::  +test-definitions: a user rule reduces and prints the confirmation
::  line exactly as SPEC-DESK.md §4.4 specifies.
::
++  test-definitions
  ^-  tang
  =/  r1  (run default-env "twice x -> x x")
  =/  r2  (run session.r1 "twice vvv")
  %+  weld
    %+  category  "rule definition confirms"
    (expect-eq !>(["defined twice (arity 1): twice x -> x x"]~) !>(out.r1))
  %+  category  "rule definition reduces"
  (expect-eq !>(["vvv vvv  [1 step]"]~) !>(out.r2))
::
::  +test-shadow-builtin-errors: redefining a built-in is a hard error
::  (SPEC.md §7).
::
++  test-shadow-builtin-errors
  ^-  tang
  =/  r  (run default-env "K := I")
  =/  ok=?
    ?~  out.r  %.n
    =(i.out.r "! cannot shadow built-in 'K'")
  %+  category  "shadowing K errors"
  (expect !>(ok))
::
::  +test-magics: %fuel/%undef/%ski round out the five required magics
::  (SPEC-DESK.md §3).
::
++  test-magics
  ^-  tang
  =/  r1  (run default-env "%fuel 25")
  =/  r2  (run session.r1 "M M")
  %+  weld
    %+  category  "%fuel sets the session budget"
    (expect-eq !>(["fuel (max_steps) set to 25"]~) !>(out.r1))
  =/  ok=?
    ?~  out.r2  %.n
    ?~  t.out.r2  %.n
    =(i.t.out.r2 "⚠ no normal form after 25 steps (fuel exhausted)")
  %+  category  "fuel exhaustion warns, does not crash"
  (expect !>(ok))
--
