::  /sur/aviary: types for the %aviary combinator-calculus engine (SPEC-DESK.md §4)
::
::    Term representation note (deviation from the literal SPEC-DESK.md
::    snippet `+$  term  $%([%atom name=@t] [%app fun=term arg=term])`):
::
::    that exact shape -- a directly self-referential $% union with a cell
::    sibling in the same core -- reproducibly crashes Hoon's type-checker
::    with `%over` ("recover: dig: over") the moment the enclosing core has
::    *any* other +$ arm alongside it (confirmed empirically: `term` alone
::    in its own core is fine; `term` plus one unrelated sibling mold, e.g.
::    `bird`, blows up on the core's own compilation, before anything even
::    references it). Wrapping the atom case in `$@` (atom-or-cell) instead
::    of a `$%` cell tag sidesteps it completely and was verified to compile
::    reliably even with all four molds together. So: an "atom" term is
::    represented as a bare `@t` (the name itself) rather than a tagged
::    `[%atom name=@t]` cell; an "app" term keeps the `%app` tag with
::    `fun`/`arg` fields exactly as specified. Same information, same
::    field-access idioms for the %app case (`fun.t`/`arg.t`); the only
::    change is that an atom term is `t` itself rather than `name.t`, and
::    dispatch uses `?@`/`?^` instead of `?-  -.t`.
::
|%
+$  term  $@(@t [%app fun=term arg=term])
::
::  $bird: one registry row (SPEC-DESK.md §4.2)
::
::    name:  canonical name (ASCII for most birds; Unicode for Ê/Φ/Ψ, whose
::           ASCII spellings E^/Phi/Psi are handled as a separate alias map)
::    disp:  preferred display form (Unicode subscripts where applicable)
::    arity: number of formal arguments the rule consumes
::    rule:  canonical rule RHS text over formal vars a b c d e f g, parsed
::           by the engine's own parser on demand -- the text is the source
::           of truth, so the registry cross-test and the code cannot drift
::
+$  bird  [name=@t disp=@t arity=@ud rule=tape]
::
::  $def: a user (session) definition -- an alias (arity 0, unfolds to
::  body) or a rule (arity n, substitutes vars into rhs)
::
+$  def   $%([%alias body=term] [%rule arity=@ud vars=(list @t) rhs=term])
::
::  $env: per-session state -- user definitions plus the session's fuel
::  (step budget); the size cap is fixed, not session-adjustable
::
+$  env   [defs=(map @t def) fuel=@ud]
--
