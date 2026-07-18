::  test-engine-cases.hoon: the §8 test battery, appended after
::  sur/aviary.hoon + lib/aviary.hoon by tests/test-engine.sh.
::
::  Produces (list tape): each entry is a failing case's label; an empty
::  list (printed by `urbit eval` as `<<>>`) means every case passed.
::
::  Uses the engine's own internals directly (birds, reduce, parse-rule-
::  text, subst, decomp, expand, run, default-env, ...) since this file
::  is chained onto the same core as lib/aviary.hoon via test-engine.sh's
::  `=>`-pipeline.
::
=>
|%
++  is-err
  |=  t=tape
  ^-  ?
  ?~  t  %.n
  =(i.t '!')
::
++  fresh-name
  |=  [pfx=@t i=@ud]
  ^-  @t
  (cat 3 pfx (add 48 i))
::
++  fresh-names
  |=  [pfx=@t n=@ud]
  ^-  (list @t)
  (turn (gulf 1 n) |=(i=@ud (fresh-name pfx i)))
::
++  ski-of
  |=  [=env name=@t]
  ^-  term
  =/  r  (expand env name ~ %.n)
  ?>  ?=(%& -.r)
  p.r
::
::  +ck: turn a boolean check into the (list tape) shape g2/g4/g6 use --
::  centralizing the cast here (rather than repeating ?: ... ~ ["label" ~]
::  inline at each call site) avoids feeding `zing`/`weld` a list of
::  independently, narrowly-inferred literal shapes, which otherwise
::  fails to compile (mull-grow) the same way the engine's own tok/@c
::  list literals did (see lib/aviary.hoon's header comment).
::
++  ck
  |=  [ok=? label=tape]
  ^-  (list tape)
  ?:  ok  ~
  [label ~]
--
::
=/  e0  default-env
::
::  --- §8.1: every bird, one step -----------------------------------------
::
=/  g1
  %+  murn  birds
  |=  =bird
  ^-  (unit tape)
  =/  ar  arity.bird
  =/  formals  (formals-for ar)
  =/  fresh  (fresh-names 'z' ar)
  =/  args=(list term)  fresh
  =/  input  (mk-app name.bird args)
  =/  got  rt:(reduce e0(fuel 1) input)
  =/  want  (subst (parse-rule-text rule.bird) (zip-map formals args))
  ?:  =(got want)  ~
  `(weld "bird-one-step:" (trip name.bird))
::
::  --- §8.2: laziness -------------------------------------------------------
::
=/  g2
  ^-  (list tape)
  %-  zing
  :~
    ::  K ▲ (M M) => ▲ in exactly 1 step
    =/  r  (run e0 "K ▲ (M M)")
    (ck =(out.r ["▲  [1 step]"]~) "laziness:K-1step")
  ::
    ::  S K (M M) ▲ terminates at a normal form (never touches M M, which
    ::  alone would exhaust fuel -- so a %normal status here already
    ::  proves the laziness)
    =/  parsed  (parse-rule-text "S K (M M) ▲")
    =/  res  (reduce e0 parsed)
    (ck &(=(rt.res '▲') =(status.res %normal)) "laziness:SK(MM)x")
  ::
    ::  M M alone exhausts fuel with the warning line, no crash
    =/  r  (run e0 "M M")
    =/  has-warn=?
      &(?=(^ out.r) (lien `(list tape)`out.r |=(t=tape ?=(^ (find "⚠ no normal form after" t)))))
    (ck has-warn "laziness:MM-fuel-warning")
  ==
::
::  --- §8.3: full normalization (Unicode round-trip) ------------------------
::
=/  g3
  =/  r  (run e0 "B ▲ 🟢 (K ◆ ●)")
  (ck =(out.r ["▲ (🟢 ◆)  [2 steps]"]~) "fullnorm:unicode")
::
::  --- §8.4: definitions -----------------------------------------------------
::
=/  g4
  ^-  (list tape)
  %-  zing
  :~
    ::  rule def reduces and %ski-expands
    =/  r1  (run e0 "dbl x -> x x")
    =/  s1  session.r1
    =/  r2  (run s1 "dbl z9")
    =/  s2  session.r2
    =/  r3  (run s2 "%ski dbl")
    %-  zing
    :~  (ck =(out.r1 ["defined dbl (arity 1): dbl x -> x x"]~) "defs:rule-confirm")
        (ck =(out.r2 ["z9 z9  [1 step]"]~) "defs:rule-reduces")
        (ck &(?=(^ out.r3) !(is-err -.out.r3)) "defs:rule-ski-ok")
    ==
  ::
    ::  alias stays folded when unused (K y5 myalias => y5, laziness even
    ::  though the alias body itself would blow up if forced)
    =/  ra1  (run e0 "myalias := M")
    =/  ra2  (run session.ra1 "K y5 myalias")
    (ck =(out.ra2 ["y5  [1 step]"]~) "defs:alias-folded")
  ::
    ::  shadowing a built-in errors
    =/  rs  (run e0 "B := I")
    (ck &(?=(^ out.rs) (is-err -.out.rs)) "defs:shadow-builtin-errors")
  ::
    ::  recursive def reduces (under laziness) but %ski errors
    =/  rr1  (run e0 "loopy x -> loopy x")
    =/  rr2  (run session.rr1 "K y6 (loopy y6)")
    =/  rr3  (run session.rr2 "%ski loopy")
    %-  zing
    :~  (ck =(out.rr2 ["y6  [1 step]"]~) "defs:recursive-reduces")
        (ck &(?=(^ out.rr3) (is-err -.out.rr3)) "defs:recursive-ski-errors")
    ==
  ::
    ::  %undef works
    =/  ru1  (run e0 "again x -> x")
    =/  ru2  (run session.ru1 "%undef again")
    =/  ru3  (run session.ru2 "%undef again")
    %-  zing
    :~  (ck =(out.ru2 ["undefined again"]~) "defs:undef-works")
        (ck &(?=(^ out.ru3) (is-err -.out.ru3)) "defs:undef-twice-errors")
    ==
  ==
::
::  --- §8.5: expansion soundness (sample spanning arities 1-7) --------------
::
=/  sample=(list @t)
  :~  'I'  'K'  'S'  'Q4'  'B1'  'G'  'D2'  'R**'  'Ê'  'W\''
  ==
=/  g5a
  %+  murn  sample
  |=  name=@t
  ^-  (unit tape)
  =/  c  (need (lookup-comb e0 name))
  =/  ar  arity.c
  =/  fresh  (fresh-names 'w' ar)
  =/  args=(list term)  fresh
  =/  direct  rt:(reduce e0 (mk-app name args))
  =/  ex  (ski-of e0 name)
  =/  expanded  rt:(reduce e0 (mk-app ex args))
  ?:  =(direct expanded)  ~
  `(weld "expand-sound:" (trip name))
::
::  Y is unbounded to reduce fully; check its expansion is at least
::  behaviorally on-track: (expand Y) applied to a fresh f, reduced with
::  a small bounded fuel, has f as its ultimate stuck head (mirrors the
::  Python suite's "reduces (bounded) to a term whose head is f").
::
=/  g5b
  =/  ex  (ski-of e0 'Y')
  =/  bounded  e0(fuel 40)
  =/  res  (reduce bounded (mk-app ex ~['wf']))
  =/  hd  hed:(decomp rt.res)
  (ck =(hd 'wf') "expand-sound:Y-bounded")
::
::  --- §8.6: statement plumbing ----------------------------------------------
::
=/  g6
  ^-  (list tape)
  %-  zing
  :~
    ::  %fuel 50 then M M stops at 50
    =/  rf1  (run e0 "%fuel 50")
    =/  rf2  (run session.rf1 "M M")
    =/  expected-fuel50=(list tape)
      :~  "M M  [50 steps]"
          "⚠ no normal form after 50 steps (fuel exhausted)"
      ==
    (ck =(out.rf2 expected-fuel50) "plumb:fuel-50")
  ::
    ::  %defs lists a definition
    =/  rd1  (run e0 "tri x -> x x x")
    =/  rd2  (run session.rd1 "%defs")
    (ck =(out.rd2 ["tri x -> x x x  (arity 1)"]~) "plumb:defs-lists")
  ::
    ::  comments and blank lines are no-ops
    =/  rc  (run e0 "# just a comment")
    =/  rb  (run e0 "")
    %-  zing
    :~  (ck =(out.rc ~) "plumb:comment-noop")
        (ck =(out.rb ~) "plumb:blank-noop")
    ==
  ::
    ::  unknown magic errors
    =/  ru  (run e0 "%bogus")
    (ck &(?=(^ out.ru) (is-err -.out.ru)) "plumb:unknown-magic-errors")
  ==
::
::  --- §8+: %trace (v1.1, added post-v1 per SPEC.md §6.3/§9) ---------------
::
=/  g7
  ^-  (list tape)
  %-  zing
  :~
    ::  exact line format: no label pads to width 4 with spaces, step
    ::  right-justifies to width 4, then two spaces, then the term
    =/  rt  (run e0 "%trace K x1 (M x1)")
    =/  expected-trace=(list tape)
      :~  "       0  K x1 (M x1)"
          "K      1  x1"
      ==
    (ck =(out.rt expected-trace) "trace:exact-format")
  ::
    ::  the label is the canonical registry name, not the display form --
    ::  Ê contracting shows "Ê", not some ascii-only rendering, and a
    ::  user rule name longer than 4 chars is not truncated or re-padded
    =/  rt2  (run e0 "myrule x -> x x")
    =/  rt3  (run session.rt2 "%trace myrule x9")
    =/  expected-label=(list tape)
      :~  "       0  myrule x9"
          "myrule   1  x9 x9"
      ==
    (ck =(out.rt3 expected-label) "trace:label-format")
  ::
    ::  fuel exhaustion during %trace: full trace up to the limit, then
    ::  the same warning line a plain expression would show -- not an
    ::  error, and no crash
    =/  rf1  (run e0 "%fuel 5")
    =/  rf2  (run session.rf1 "%trace M M")
    =/  expected-mm=(list tape)
      :~  "       0  M M"
          "M      1  M M"
          "M      2  M M"
          "M      3  M M"
          "M      4  M M"
          "M      5  M M"
          "⚠ no normal form after 5 steps (fuel exhausted)"
      ==
    (ck =(out.rf2 expected-mm) "trace:fuel-exhaustion")
  ::
    ::  long traces elide the middle beyond 200 lines under default fuel
    =/  rl  (run e0 "%trace M M")
    =/  n  (lent out.rl)
    =/  has-marker  (lien `(list tape)`out.rl |=(l=tape ?=(^ (find "elided" l))))
    %-  zing
    :~  (ck =(n 202) "trace:elide-total-lines")
        (ck has-marker "trace:elide-has-marker")
    ==
  ==
::
::  --- §8+: %whnf (v1.1, added post-v1 per SPEC.md §6.1/§9) ----------------
::
=/  g8
  ^-  (list tape)
  %-  zing
  :~
    ::  a head redex fully consumes its args and stops -- same result a
    ::  full reduce would give when the discarded arg is never forced
    =/  r1  (run e0 "%whnf K x1 (M x1)")
    (ck =(out.r1 ["x1  [whnf, 1 step]"]~) "whnf:head-redex")
  ::
    ::  the defining difference from a full reduce: an under-applied head
    ::  (B needs 3 args, has 2) is already stuck, so %whnf stops at 0
    ::  steps *without* descending into the arguments -- (M x2) is left
    ::  wholly unreduced, whereas a plain expression normalizes it
    =/  r2  (run e0 "%whnf B x1 (M x2)")
    =/  r3  (run e0 "B x1 (M x2)")
    %-  zing
    :~  (ck =(out.r2 ["B x1 (M x2)  [whnf, 0 steps]"]~) "whnf:stuck-head-no-descend")
        (ck =(out.r3 ["B x1 (x2 x2)  [1 step]"]~) "whnf:plain-expr-descends-for-contrast")
    ==
  ::
    ::  a bare stuck atom is whnf at 0 steps (status is %whnf, never
    ::  %normal, even though nothing was contracted)
    =/  r4  (run e0 "%whnf x1")
    (ck =(out.r4 ["x1  [whnf, 0 steps]"]~) "whnf:bare-atom-zero-steps")
  ::
    ::  fuel exhaustion under %whnf: single result line only, no separate
    ::  "⚠" warning line (matches the Python reference's _finish_reduction,
    ::  which %whnf alone uses -- unlike a plain expression or %trace)
    =/  rf1  (run e0 "%fuel 3")
    =/  rf2  (run session.rf1 "%whnf M M")
    (ck =(out.rf2 ["M M  [3 steps]"]~) "whnf:fuel-exhaustion-no-warning-line")
  ==
::
::  --- §8+: %size (v1.1, added post-v1 per SPEC.md §6.2/§9) ----------------
::
=/  g9
  ^-  (list tape)
  %-  zing
  :~
    ::  bare %size prints the current value (default 100000, same cap as
    ::  the old fixed +size-cap)
    =/  r1  (run e0 "%size")
    (ck =(out.r1 ["size (max_size) = 100000"]~) "size:bare-prints-default")
  ::
    ::  %size N sets it and confirms; then a lowered %size actually bounds
    ::  reduction -- "Y M" genuinely grows (unlike "M M", which stays
    ::  constant size) -- exceeding a %size 50 cap partway through,
    ::  producing the "⚠ term exceeded" warning line (not an error), same
    ::  shape as a %fuel exhaustion (both checks share r2's session, so
    ::  they must live in the same list entry -- sibling entries of a `:~`
    ::  list don't see each other's `=/` bindings)
    =/  r2  (run e0 "%size 50")
    =/  r3  (run session.r2 "Y M")
    =/  has-warn=?
      &(?=(^ out.r3) (lien `(list tape)`out.r3 |=(t=tape ?=(^ (find "⚠ term exceeded 50 atoms" t)))))
    %-  zing
    :~  (ck =(out.r2 ["size (max_size) set to 50"]~) "size:set-confirms")
        (ck has-warn "size:lowered-cap-triggers-warning")
    ==
  ::
    ::  bad argument errors, same shape as %fuel
    =/  r4  (run e0 "%size 0")
    =/  r5  (run e0 "%size nope")
    %-  zing
    :~  (ck &(?=(^ out.r4) (is-err -.out.r4)) "size:zero-errors")
        (ck &(?=(^ out.r5) (is-err -.out.r5)) "size:non-numeric-errors")
    ==
  ==
::
::  --- §8+: %ascii (v1.1, added post-v1 per SPEC.md §4.3/§9) ---------------
::
=/  g10
  ^-  (list tape)
  %-  zing
  :~
    ::  default (ascii off) renders a bird whose display differs from its
    ::  canonical name in Unicode subscript form
    =/  r1  (run e0 "Q1")
    (ck =(out.r1 ["Q₁  [normal form]"]~) "ascii:default-is-unicode")
  ::
    ::  %ascii on confirms, then the same bird renders by its canonical
    ::  (ASCII) name instead
    =/  ra  (run e0 "%ascii on")
    =/  rb  (run session.ra "Q1")
    %-  zing
    :~  (ck =(out.ra ["ascii mode on"]~) "ascii:on-confirms")
        (ck =(out.rb ["Q1  [normal form]"]~) "ascii:on-renders-ascii")
    ==
  ::
    ::  bad argument errors
    =/  rc  (run e0 "%ascii bogus")
    (ck &(?=(^ out.rc) (is-err -.out.rc)) "ascii:bad-arg-errors")
  ==
::
;:  weld  g1  g2  g3  g4  g5a  g5b  g6  g7  g8  g9  g10
==
