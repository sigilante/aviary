::  Aviary - combinator-calculus REPL via %shoe, and a caderno kernel
::
::    %eval-command (programmatic execution) and the /x/sole/sessions scry
::    (kernel discovery) both live in the vendored lib/shoe.hoon; this
::    agent needs no special code for either (SPEC-DESK.md §1, §5).
::
/+  default-agent, shoe, dbug
/+  *aviary
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
++  tab-list  tab-list:des
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
