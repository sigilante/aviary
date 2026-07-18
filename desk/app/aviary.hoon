::  Aviary - combinator-calculus REPL via %shoe, and a caderno kernel
::
::    %eval-command (programmatic execution) and the /x/sole/sessions scry
::    (kernel discovery) both live in the vendored lib/shoe.hoon; this
::    agent needs no special code for either (SPEC-DESK.md §1, §5).
::
/+  default-agent, shoe, dbug
/+  *aviary
/+  auto=language-server-complete
::
|%
+$  versioned-state  $%  [%0 state-0]  ==
+$  state-0
  $:  %0
      sessions=(map sole-id:shoe env)
  ==
+$  command  tape   ::  raw statement text; ++run does the real parsing
+$  card  card:shoe
::
::  +lines-of: split a (possibly multi-line) %eval-command payload into
::  physical lines -- kept outside the shoe door below since agent:gall's
::  core shape is checked exactly (an extra arm on the door itself fails
::  Gall's "core-nice" arm-count check).
::
++  lines-of
  |=  t=tape
  ^-  (list tape)
  =/  cur=tape  ~
  =/  acc=(list tape)  ~
  |-
  ^-  (list tape)
  ?~  t
    (flop `(list tape)`[(flop cur) acc])
  ?:  =(i.t `@`10)
    $(t t.t, cur ~, acc `(list tape)`[(flop cur) acc])
  $(t t.t, cur `tape`[i.t cur])
::
::  --- +tab-list candidates -----------------------------------------------
::
::    Aviary's half of "completion/tab-list beyond shoe's default"
::    (SPEC-DESK.md §1/§10's deferred item): supplying the actual
::    candidates (bird names + aliases, magic names, the session's own
::    user definitions) is squarely Aviary's job -- only Aviary knows
::    this vocabulary. The generic prefix-filtering/longest-match
::    machinery that turns this list into a live Tab keystroke's effect
::    is already vendored (lib/language-server-complete.hoon, called
::    "auto" here, matching lib/shoe.hoon's own internal alias) and
::    wired up by /lib/shoe's `+tab` arm for any real sole session.
::
::    Whether a *caderno notebook cell* ever exercises this is a
::    separate, Caderno-side question -- see the sigilante/caderno issue
::    filed alongside this change. This code path is exactly as useful
::    interactively (dojo, or any other real sole session) regardless
::    of that.
::
::  +magic-help: one-line description per magic name, shown as each
::  candidate's detail tank.
::
++  magic-help
  ^-  (map @t tape)
  %-  malt
  :~  ['%ski' "basis-expand to S/K/I, no reduction"]
      ['%sk' "basis-expand to strict S/K, no reduction"]
      ['%trace' "step-by-step reduction trace"]
      ['%whnf' "reduce to weak head normal form only"]
      ['%fuel' "get/set the session's step budget"]
      ['%size' "get/set the session's term-size ceiling"]
      ['%ascii' "toggle ASCII vs Unicode display"]
      ['%birds' "list the whole bird registry"]
      ['%whatis' "one bird/definition's card"]
      ['%defs' "list user definitions"]
      ['%undef' "remove a user definition"]
  ==
::
::  +bird-candidates: every bird's canonical name plus every alias key
::  (E^, Phi, Psi -- Theta is handled separately below, since Θ is not a
::  $bird row), each with a short detail tank.
::
++  bird-candidates
  ^-  (list (option:auto tank))
  %-  zing
  %+  turn  birds
  |=  b=bird
  ^-  (list (option:auto tank))
  =/  detail=tank
    :-  %leaf
    %+  weld  (trip (~(got by bird-names) name.b))
    (weld " (arity " (weld (render-ud arity.b) ")"))
  :-  [name.b detail]
  %+  turn  (aliases-for name.b)
  |=  a=@t
  ^-  (option:auto tank)
  [a leaf+(weld "alias for " (trip name.b))]
::
::  +magic-candidates: every magic name, detail from +magic-help.
::
++  magic-candidates
  ^-  (list (option:auto tank))
  %+  turn  ~(tap by magic-help)
  |=  [k=@t v=tape]
  ^-  (option:auto tank)
  [k leaf+v]
::
::  +def-candidates: the session's own user definitions, detail
::  rendered the same way %defs itself would show them.
::
++  def-candidates
  |=  session=env
  ^-  (list (option:auto tank))
  %+  turn  ~(tap by defs.session)
  |=  [p=@t q=def]
  ^-  (option:auto tank)
  [p leaf+(render-def p q %.n)]
::
++  tab-candidates
  |=  session=env
  ^-  (list (option:auto tank))
  ;:  weld
    bird-candidates
    :~  ['Θ' leaf+"built-in alias := U U"]
        ['Theta' leaf+"alias for Θ"]
    ==
    magic-candidates
    (def-candidates session)
  ==
--
::
=|  state-0
=*  state  -
::
%-  agent:dbug
^-  agent:gall
%-  (agent:shoe command)
^-  (shoe:shoe command)
|_  =bowl:gall
+*  this  .
    def   ~(. (default-agent this %|) bowl)
    des   ~(. (default:shoe this command) bowl)
::
++  on-init
  ^-  (quip card _this)
  `this
::
++  on-save   !>(state)
::
++  on-load
  |=  old=vase
  ^-  (quip card _this)
  `this
::
++  on-poke    on-poke:def
++  on-watch   on-watch:def
++  on-leave   on-leave:def
++  on-peek    on-peek:def
++  on-agent   on-agent:def
++  on-arvo    on-arvo:def
++  on-fail    on-fail:def
::
::  +command-parser: (stag | (star next)), NOT (star prn) -- prn is
::  ASCII-only and would reject Q₁/▲/🟢 at the keystroke-parser layer
::  before the engine's own (Unicode-aware) parser ever sees them
::  (SPEC-DESK.md §5).
::
++  command-parser
  |=  =sole-id:shoe
  ^+  |~(nail *(like [? command]))
  (stag | (star next))
::
++  tab-list
  |=  =sole-id:shoe
  ^-  (list (option:auto tank))
  (tab-candidates (~(gut by sessions) sole-id default-env))
::
++  can-connect
  |=  =sole-id:shoe
  ^-  ?
  =(our src):bowl
::
++  on-connect
  |=  =sole-id:shoe
  ^-  (quip card _this)
  ::  shoe's on-watch already emits the initial %pro; don't double it
  `this
::
++  on-disconnect
  |=  =sole-id:shoe
  ^-  (quip card _this)
  `this
::
::  +on-command: look up (or lazily create, with default fuel) the
::  session's env, run the statement, emit each output line as a %txt
::  fact, persist the updated env. No echo of input; no %pro here --
::  the interactive path prompts via shoe, and the %eval-command path
::  appends its own terminal %pro in the vendored wrapper (SPEC-DESK.md
::  §5). A cmd may be a whole (possibly multi-line) %eval-command
::  payload; ++run is one-statement-per-line, so split on "\0a" and
::  thread the env through each line in turn.
::
++  on-command
  |=  [=sole-id:shoe cmd=command]
  ^-  (quip card _this)
  =/  prior=env  (~(gut by sessions) sole-id default-env)
  =/  lines=(list tape)  (lines-of cmd)
  =/  out-lines=(list tape)  ~
  =/  cur=env  prior
  |-
  ^-  (quip card _this)
  ?~  lines
    :_  this(sessions (~(put by sessions) sole-id cur))
    %+  turn  (flop out-lines)
    |=  ln=tape
    [%shoe ~[sole-id] %sole [%txt ln]]
  =/  res  (run cur i.lines)
  $(lines t.lines, cur session.res, out-lines (weld (flop out.res) out-lines))
--
