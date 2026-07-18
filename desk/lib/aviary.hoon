::  /lib/aviary: the combinator-calculus engine (SPEC-DESK.md §4)
::
::    Pure library -- no Gall/agent imports. The public entry point is
::    ++run, |=([env line=tape] [out=(list tape) =env]): it executes one
::    statement (one physical line) and returns output lines plus the
::    (possibly updated) session environment. The agent (/app/aviary) is a
::    thin transport shim around this.
::
::    Unicode: input is decoded from UTF-8 to codepoints with +tuba (SPEC-
::    DESK.md §4.1 says "+turf", but the actual stdlib gate performing this
::    -- tape-of-utf8-bytes to (list @c) -- is +tuba (composed from +taft/
::    +rip in zuse); there is no +turf in the kelvin-408 standard library.
::    We treat this as a naming slip in the spec and use +tuba/+tufa, which
::    are exactly the "+tuft/+taft composition" the spec describes. Tokens
::    are re-encoded to @t with +tufa + +crip. Malformed UTF-8 makes +tuba
::    crash (via internal ?> assertions in +taft); we catch that crash with
::    +mule and turn it into a parse error instead of letting it kill the
::    Gall event (SPEC-DESK.md §4.1's "malformed UTF-8 must produce a parse
::    error, not a crash").
::
::    Name canonicalization (SPEC-DESK.md §4.1, SPEC.md §4.3 minus NFC):
::    subscript digits U+2080-U+2089 -> ASCII digits, U+2032 (prime) and
::    U+00B9 (superscript one) -> ASCII apostrophe. No Unicode NFC
::    normalization (not in the Hoon standard library): a decomposed
::    combining-circumflex E will NOT match precomposed Ê. Precomposed Ê
::    and the ASCII alias E^ both work (E^ is a registry alias, not a
::    normalization rule).
::
/-  *aviary
|%
::  +size-cap: fixed term-size ceiling (SPEC-DESK.md §4.3), atoms
::  +default-fuel: default step budget for a fresh session
::
++  size-cap      100.000
++  default-fuel  10.000
::
::  +default-env: fresh per-session state (used by the agent on first
::  contact with a session)
::
++  default-env  ^-(env [~ default-fuel])
::
::  +y-ski: Y's explicit S/K/I override (SPEC.md §5.2, Curry's form) --
::  bracket abstraction cannot derive a finite S/K/I form for a genuinely
::  self-referential rule ("a (Y a)"), so Y alone carries this override,
::  looked up by name in ++lookup-comb rather than as a $bird field (the
::  $bird mold given by SPEC-DESK.md §4 has no room for one).
::
++  y-ski  "S (K (S I I)) (S (S (K S) K) (K (S I I)))"
::
::  +birds: the 50-bird registry (SPEC-DESK.md §4.2), a strictly formatted
::  literal -- one row per line, exactly `['NAME' 'DISP' ARITY "RULE"]` --
::  cross-checked byte-for-byte against aviary_kernel/birds.py by
::  tests/test_hoon_registry.py. Column 1 is the canonical lookup name
::  (ASCII for most birds; Unicode itself for Ê/Φ/Ψ, whose ASCII spellings
::  are separate ++aliases entries, matching birds.py's name/aliases
::  split). Column 4 is the rule RHS in canonical text over formal
::  variables a..g, parsed by ++parse-rule-text (the engine's own parser)
::  the first time each bird is used -- the text is the single source of
::  truth, so the registry cross-test and the reducer cannot disagree.
::
++  birds
  ^-  (list bird)
  :~  ['B' 'B' 3 "a (b c)"]
      ['B1' 'B₁' 4 "a (b c d)"]
      ['B2' 'B₂' 5 "a (b c d e)"]
      ['B3' 'B₃' 4 "a (b (c d))"]
      ['C' 'C' 3 "a c b"]
      ['C*' 'C*' 4 "a b d c"]
      ['C**' 'C**' 5 "a b c e d"]
      ['D' 'D' 4 "a b (c d)"]
      ['D1' 'D₁' 5 "a b c (d e)"]
      ['D2' 'D₂' 5 "a (b c) (d e)"]
      ['E' 'E' 5 "a b (c d e)"]
      ['Ê' 'Ê' 7 "a (b c d) (e f g)"]
      ['F' 'F' 3 "c b a"]
      ['F*' 'F*' 4 "a d c b"]
      ['F**' 'F**' 5 "a b e d c"]
      ['G' 'G' 4 "a d (b c)"]
      ['H' 'H' 3 "a b c b"]
      ['I' 'I' 1 "a"]
      ['I*' 'I*' 2 "a b"]
      ['I**' 'I**' 3 "a b c"]
      ['J' 'J' 4 "a b (a d c)"]
      ['K' 'K' 2 "a"]
      ['Ki' 'Ki' 2 "b"]
      ['KM' 'KM' 2 "b b"]
      ['KM\'' 'KM\'' 2 "a a"]
      ['L' 'L' 2 "a (b b)"]
      ['M' 'M' 1 "a a"]
      ['M2' 'M₂' 2 "a b (a b)"]
      ['O' 'O' 2 "b (a b)"]
      ['Φ' 'Φ' 4 "a (b d) (c d)"]
      ['Ψ' 'Ψ' 4 "a (b c) (b d)"]
      ['Q' 'Q' 3 "b (a c)"]
      ['Q1' 'Q₁' 3 "a (c b)"]
      ['Q2' 'Q₂' 3 "b (c a)"]
      ['Q3' 'Q₃' 3 "c (a b)"]
      ['Q4' 'Q₄' 3 "c (b a)"]
      ['R' 'R' 3 "b c a"]
      ['R*' 'R*' 4 "a c d b"]
      ['R**' 'R**' 5 "a b d e c"]
      ['S' 'S' 3 "a c (b c)"]
      ['T' 'T' 2 "b a"]
      ['U' 'U' 2 "b (a a b)"]
      ['V' 'V' 3 "c a b"]
      ['V*' 'V*' 4 "a d b c"]
      ['V**' 'V**' 5 "a b e c d"]
      ['W' 'W' 2 "a b b"]
      ['W*' 'W*' 3 "a b c c"]
      ['W**' 'W**' 4 "a b c d d"]
      ['W\'' 'W\'' 2 "b a a"]
      ['Y' 'Y' 1 "a (Y a)"]
  ==
::
::  +aliases: ASCII spellings for the birds whose canonical name is
::  Unicode, plus Theta (SPEC-DESK.md §4.2's "small separate alias list").
::  Θ itself is not a $bird row -- it is preloaded as if the user had
::  typed `Θ := U U` (SPEC.md §5.2), handled specially in ++lookup-comb/
::  ++disp-name/shadow-checks, never stored in env's user defs map.
::
++  aliases
  ^-  (map @t @t)
  %-  malt
  :~  ['E^' 'Ê']
      ['Phi' 'Φ']
      ['Psi' 'Ψ']
      ['Theta' 'Θ']
  ==
::
++  birds-map
  ^-  (map @t bird)
  %-  malt
  (turn birds |=(b=bird [name.b b]))
::
::  --- internal types ---------------------------------------------------
::
+$  tok    $%([%lpar ~] [%rpar ~] [%bind ~] [%arrow ~] [%atom p=@t])
+$  frame  [hed=@t done=(list term) todo=(list term)]
+$  mode   $%([%descend hed=@t args=(list term)] [%ascend result=term])
+$  comb   [arity=@ud formals=(list @t) body=term ski=(unit term)]
::
::  --- term helpers -------------------------------------------------------
::
++  mk-app
  |=  [hed=term args=(list term)]
  ^-  term
  ?~  args  hed
  $(hed [%app hed i.args], args t.args)
::
++  decomp
  |=  t=term
  ^-  [hed=@t args=(list term)]
  =|  args=(list term)
  |-
  ^-  [hed=@t args=(list term)]
  ?@  t  [t args]
  $(t fun.t, args [arg.t args])
::
++  term-size
  |=  t=term
  ^-  @ud
  =|  n=@ud
  =/  stack=(list term)  [t ~]
  |-
  ^-  @ud
  ?~  stack  n
  ?@  i.stack  $(stack t.stack, n +(n))
  $(stack [fun.i.stack arg.i.stack t.stack])
::
++  subst
  |=  [t=term m=(map @t term)]
  ^-  term
  ?@  t  (~(gut by m) t t)
  [%app (subst fun.t m) (subst arg.t m)]
::
++  zip-map
  |=  [ks=(list @t) vs=(list term)]
  ^-  (map @t term)
  =|  m=(map @t term)
  |-
  ^-  (map @t term)
  ?~  ks  m
  ?~  vs  m
  $(ks t.ks, vs t.vs, m (~(put by m) i.ks i.vs))
::
++  formals-for
  |=  n=@ud
  ^-  (list @t)
  (scag n `(list @t)`~['a' 'b' 'c' 'd' 'e' 'f' 'g'])
::
++  free-in
  |=  [x=@t t=term]
  ^-  ?
  ?@  t  =(t x)
  |((free-in x fun.t) (free-in x arg.t))
::
::  --- name resolution & display ------------------------------------------
::
++  resolve-name
  |=  name=@t
  ^-  @t
  (~(gut by aliases) name name)
::
++  disp-name
  |=  name=@t
  ^-  @t
  =/  rname  (resolve-name name)
  =/  b  (~(get by birds-map) rname)
  ?^  b  disp.u.b
  ?:  =(rname 'Θ')  'Θ'
  name
::
++  pretty
  |=  t=term
  ^-  tape
  ?@  t  (trip (disp-name t))
  =/  fn-s  (pretty fun.t)
  =/  arg-s  (pretty arg.t)
  =/  arg-s2  ?:(?=(^ arg.t) (weld "(" (weld arg-s ")")) arg-s)
  (weld fn-s (weld " " arg-s2))
::
::  --- registry / definition lookup --------------------------------------
::
++  lookup-comb
  |=  [session=env name=@t]
  ^-  (unit comb)
  =/  rname  (resolve-name name)
  =/  b  (~(get by birds-map) rname)
  ?^  b
    =/  ar  arity.u.b
    :-  ~
    :*  ar  (formals-for ar)  (parse-rule-text rule.u.b)
        ?:(=(rname 'Y') `(parse-rule-text y-ski) ~)
    ==
  ?:  =(rname 'Θ')
    `[0 ~ [%app 'U' 'U'] ~]
  =/  d  (~(get by defs.session) rname)
  ?~  d  ~
  ?-  -.u.d
    %alias  `[0 ~ body.u.d ~]
    %rule   `[arity.u.d vars.u.d rhs.u.d ~]
  ==
::
::  --- lexer ---------------------------------------------------------------
::
++  is-ws  |=(c=@c |(=(c ' ') =(c 9) =(c 13)))
::
++  is-op2-bind
  |=  cps=(list @c)
  ^-  ?
  ?&  ?=([@ @ *] cps)
      =(i.cps ':')
      =(i.t.cps '=')
  ==
::
++  is-op2-arrow
  |=  cps=(list @c)
  ^-  ?
  ?&  ?=([@ @ *] cps)
      =(i.cps '-')
      =(i.t.cps '>')
  ==
::
::  +canon-cp: targeted per-codepoint canonicalization (SPEC-DESK.md §4.1) --
::  subscript digits, prime, and superscript-one only. No general NFC (not
::  in the Hoon standard library): see the file header note.
::
++  canon-cp
  |=  c=@c
  ^-  @c
  ?:  &((gte c 0x2080) (lte c 0x2089))
    (add '0' (sub c 0x2080))
  ?:  =(c 0x2032)  `@c`39  ::  ' U+2032 prime -> ASCII apostrophe
  ?:  =(c 0xb9)  `@c`39    ::  ' U+00B9 superscript one -> ASCII apostrophe
  c
::
++  lex-line
  |=  raw=tape
  ^-  (each (list tok) tape)
  =/  m  (mule |.((tuba raw)))
  ?:  ?=(%| -.m)  [%| "malformed UTF-8"]
  =/  cps=(list @c)  p.m
  =|  out=(list tok)
  =|  acc=(list @c)
  |-
  ^-  (each (list tok) tape)
  ?~  cps
    ?~  acc  [%& (flop out)]
    [%& (flop `(list tok)`[[%atom (crip (tufa (flop `(list @c)`acc)))] out])]
  =/  c=@c  i.cps
  ?.  =(acc ~)
    ?:  |((is-ws c) =(c '#') =(c '(') =(c ')') (is-op2-bind cps) (is-op2-arrow cps))
      $(out `(list tok)`[[%atom (crip (tufa (flop `(list @c)`acc)))] out], acc ~)
    $(cps t.cps, acc `(list @c)`[(canon-cp c) acc])
  ?:  (is-ws c)  $(cps t.cps)
  ?:  =(c '#')  [%& (flop out)]
  ?:  =(c '(')  $(cps t.cps, out `(list tok)`[[%lpar ~] out])
  ?:  =(c ')')  $(cps t.cps, out `(list tok)`[[%rpar ~] out])
  ?:  (is-op2-bind cps)   $(cps ?~(t.cps ~ t.t.cps), out `(list tok)`[[%bind ~] out])
  ?:  (is-op2-arrow cps)  $(cps ?~(t.cps ~ t.t.cps), out `(list tok)`[[%arrow ~] out])
  $(cps t.cps, acc `(list @c)`[(canon-cp c) ~])
::
::  --- parser --------------------------------------------------------------
::
++  parse-one
  |=  toks=(list tok)
  ^-  (each [t=term rest=(list tok)] tape)
  ?~  toks  [%| "unexpected end of expression"]
  ?-  -.i.toks
      %lpar
    =/  inner  (parse-expr t.toks)
    ?:  ?=(%| -.inner)  inner
    ?.  ?=([[%rpar ~] *] rest.p.inner)  [%| "unmatched '('"]
    [%& t.p.inner t.rest.p.inner]
  ::
      %rpar   [%| "unexpected ')'"]
      %bind   [%| "unexpected ':='"]
      %arrow  [%| "unexpected '->'"]
      %atom   [%& p.i.toks t.toks]
  ==
::
++  parse-expr
  |=  toks=(list tok)
  ^-  (each [t=term rest=(list tok)] tape)
  =/  first  (parse-one toks)
  ?:  ?=(%| -.first)  first
  =/  acc  t.p.first
  =/  rest  rest.p.first
  |-
  ^-  (each [t=term rest=(list tok)] tape)
  ?~  rest  [%& acc rest]
  ?:  ?=(?(%rpar %bind %arrow) -.i.rest)  [%& acc rest]
  =/  nxt  (parse-one rest)
  ?:  ?=(%| -.nxt)  nxt
  $(acc [%app acc t.p.nxt], rest rest.p.nxt)
::
++  parse-expr-all
  |=  toks=(list tok)
  ^-  (each term tape)
  ?~  toks  [%| "empty statement"]
  =/  r  (parse-expr toks)
  ?:  ?=(%| -.r)  r
  ?^  rest.p.r  [%| "unexpected token"]
  [%& t.p.r]
::
::  +parse-rule-text: parses registry/y-ski rule text, which we control and
::  verify via the Hoon-side test suite (§8.1) and the Python cross-test
::  (§7) -- a parse failure here is our own bug, so it crashes rather than
::  threading an error type through every registry lookup.
::
++  parse-rule-text
  |=  t=tape
  ^-  term
  =/  lexed  (lex-line t)
  ?>  ?=(%& -.lexed)
  =/  parsed  (parse-expr-all p.lexed)
  ?>  ?=(%& -.parsed)
  p.parsed
::
::  --- reduction (SPEC-DESK.md §4.3): normal order, explicit-stack --------
::
++  cur-term
  |=  [md=mode stack=(list frame)]
  ^-  term
  =/  cur=term
    ?-  -.md
      %descend  (mk-app hed.md args.md)
      %ascend   result.md
    ==
  |-
  ^-  term
  ?~  stack  cur
  =/  fr  i.stack
  =/  remaining  (slag +((lent done.fr)) todo.fr)
  =/  next  (mk-app hed.fr :(weld done.fr [cur]~ remaining))
  $(stack t.stack, cur next)
::
++  reduce
  |=  [session=env t=term]
  ^-  [rt=term steps=@ud status=?(%normal %fuel %size)]
  =/  limit-steps  fuel.session
  =/  limit-size   size-cap
  =/  d0  (decomp t)
  =/  md=mode  [%descend hed.d0 args.d0]
  =/  stack=(list frame)  ~
  =/  steps=@ud  0
  |-
  ^-  [term @ud ?(%normal %fuel %size)]
  ?:  (gte steps limit-steps)
    [(cur-term md stack) steps %fuel]
  ?-  -.md
      %descend
    =/  hd  hed.md
    =/  ar  args.md
    =/  c  (lookup-comb session hd)
    ?:  &(?=(^ c) (gte (lent ar) arity.u.c))
      =/  consumed  (scag arity.u.c ar)
      =/  rest      (slag arity.u.c ar)
      =/  sub       (subst body.u.c (zip-map formals.u.c consumed))
      =/  d1  (decomp sub)
      =/  args2  (weld args.d1 rest)
      =/  newmd=mode  [%descend hed.d1 args2]
      =/  steps2  +(steps)
      ?:  (gth (term-size (cur-term newmd stack)) limit-size)
        [(cur-term newmd stack) steps2 %size]
      $(md newmd, steps steps2)
    ?^  ar
      =/  d2  (decomp i.ar)
      $(stack [[hd ~ ar] stack], md [%descend hed.d2 args.d2])
    $(md [%ascend hd])
  ::
      %ascend
    ?~  stack
      [result.md steps %normal]
    =/  fr  i.stack
    =/  done2  (weld done.fr [result.md]~)
    =/  remaining  (slag (lent done2) todo.fr)
    ?^  remaining
      =/  d3  (decomp i.remaining)
      $(stack [[hed.fr done2 todo.fr] t.stack], md [%descend hed.d3 args.d3])
    $(stack t.stack, md [%ascend (mk-app hed.fr done2)])
  ==
::
::  +trace-step: one recorded step for %trace (v1.1, SPEC.md §6.3) -- step 0
::  is the initial term (contracted=~); every later entry is the *whole*
::  term (ancestor context included, via +cur-term) right after one
::  contraction, tagged with the contracted combinator's canonical name.
::
+$  trace-step  [step=@ud contracted=(unit @t) tm=term]
::
::  +reduce-traced: same normal-order walk as +reduce, but also threads a
::  trace=(list trace-step) accumulator (built up reversed, +flop'd once
::  at each return point) -- kept as its own gate rather than folding a
::  trace flag into +reduce so the hot (non-traced) path stays exactly as
::  simple as it was.
::
++  reduce-traced
  |=  [session=env t=term]
  ^-  [rt=term steps=@ud status=?(%normal %fuel %size) trace=(list trace-step)]
  =/  limit-steps  fuel.session
  =/  limit-size   size-cap
  =/  d0  (decomp t)
  =/  md=mode  [%descend hed.d0 args.d0]
  =/  stack=(list frame)  ~
  =/  steps=@ud  0
  =/  trace=(list trace-step)  [[0 ~ t] ~]
  |-
  ^-  [term @ud ?(%normal %fuel %size) (list trace-step)]
  ?:  (gte steps limit-steps)
    [(cur-term md stack) steps %fuel (flop trace)]
  ?-  -.md
      %descend
    =/  hd  hed.md
    =/  ar  args.md
    =/  c  (lookup-comb session hd)
    ?:  &(?=(^ c) (gte (lent ar) arity.u.c))
      =/  consumed  (scag arity.u.c ar)
      =/  rest      (slag arity.u.c ar)
      =/  sub       (subst body.u.c (zip-map formals.u.c consumed))
      =/  d1  (decomp sub)
      =/  args2  (weld args.d1 rest)
      =/  newmd=mode  [%descend hed.d1 args2]
      =/  steps2  +(steps)
      =/  full2  (cur-term newmd stack)
      =/  trace2=(list trace-step)  [[steps2 `(resolve-name hd) full2] trace]
      ?:  (gth (term-size full2) limit-size)
        [full2 steps2 %size (flop trace2)]
      $(md newmd, steps steps2, trace trace2)
    ?^  ar
      =/  d2  (decomp i.ar)
      $(stack [[hd ~ ar] stack], md [%descend hed.d2 args.d2])
    $(md [%ascend hd])
  ::
      %ascend
    ?~  stack
      [result.md steps %normal (flop trace)]
    =/  fr  i.stack
    =/  done2  (weld done.fr [result.md]~)
    =/  remaining  (slag (lent done2) todo.fr)
    ?^  remaining
      =/  d3  (decomp i.remaining)
      $(stack [[hed.fr done2 todo.fr] t.stack], md [%descend hed.d3 args.d3])
    $(stack t.stack, md [%ascend (mk-app hed.fr done2)])
  ==
::
::  --- bracket abstraction / basis expansion (SPEC-DESK.md §4.4) ---------
::
++  bracket
  |=  [x=@t body=term]
  ^-  term
  ?@  body
    ?:  =(body x)  'I'
    [%app 'K' body]
  ?.  (free-in x body)
    [%app 'K' body]
  =/  e  fun.body
  =/  f  arg.body
  ?:  &(?@(f =(f x) |) !(free-in x e))
    e
  [%app [%app 'S' (bracket x e)] (bracket x f)]
::
++  i-to-skk
  |=  t=term
  ^-  term
  ?@  t
    ?:(=(t 'I') [%app [%app 'S' 'K'] 'K'] t)
  [%app (i-to-skk fun.t) (i-to-skk arg.t)]
::
++  expand-raw
  |=  [session=env t=term in-progress=(list @t)]
  ^-  (each term tape)
  ?^  t
    =/  f  (expand-raw session fun.t in-progress)
    ?:  ?=(%| -.f)  f
    =/  a  (expand-raw session arg.t in-progress)
    ?:  ?=(%| -.a)  a
    [%& [%app p.f p.a]]
  =/  name  t
  ?:  |(=(name 'S') =(name 'K') =(name 'I'))
    [%& t]
  =/  c  (lookup-comb session name)
  ?~  c  [%& t]
  =/  rname  (resolve-name name)
  ?:  (lien in-progress |=(x=@t =(x rname)))
    :-  %|
    (weld "cannot expand recursive combinator '" (weld (trip rname) "' to a finite S/K/I term"))
  =/  nip  [rname in-progress]
  ?^  ski.u.c
    (expand-raw session u.ski.u.c nip)
  =/  eb  (expand-raw session body.u.c nip)
  ?:  ?=(%| -.eb)  eb
  =/  result  p.eb
  =/  rformals  (flop formals.u.c)
  |-
  ^-  (each term tape)
  ?~  rformals  [%& result]
  $(result (bracket i.rformals result), rformals t.rformals)
::
++  expand
  |=  [session=env t=term in-progress=(list @t) to-sk=?]
  ^-  (each term tape)
  =/  raw  (expand-raw session t in-progress)
  ?:  ?=(%| -.raw)  raw
  ?.  to-sk  raw
  [%& (i-to-skk p.raw)]
::
::  --- plain-digit number rendering (SPEC-DESK.md §4.4: no scot %ud) -----
::
++  render-ud
  |=  n=@ud
  ^-  tape
  ?:  =(n 0)  "0"
  =|  out=tape
  |-
  ^-  tape
  ?:  =(n 0)  out
  $(n (div n 10), out [(add '0' (mod n 10)) out])
::
::  +pad-right-min4/+pad-left-min4: Python's f"{x:<4}"/f"{x:>4}" -- pad with
::  spaces to width 4 if shorter; a longer tape (e.g. a >4-char user rule
::  name in a %trace label) passes through untouched, same as Python's
::  format-spec (which never truncates).
::
++  pad-right-min4
  |=  t=tape
  ^-  tape
  ?:  (gte (lent t) 4)  t
  (weld t (reap (sub 4 (lent t)) ' '))
::
++  pad-left-min4
  |=  t=tape
  ^-  tape
  ?:  (gte (lent t) 4)  t
  (weld (reap (sub 4 (lent t)) ' ') t)
::
::  +render-trace-line: one %trace line (SPEC.md §6.3), e.g. "    0  K x
::  (M x)" (no label) or "K      1  x" (label "K", left-padded step "1").
::  The label is the contracted combinator's *canonical* name (matching
::  the Python kernel's `comb.name`), not its display/pretty form -- so
::  Ê contracts show "Ê" but Q1 shows "Q1", never "Q₁".
::
++  render-trace-line
  |=  step=trace-step
  ^-  tape
  =/  label  ?~(contracted.step "" (trip u.contracted.step))
  ;:  weld
    (pad-right-min4 label)
    (pad-left-min4 (render-ud step.step))
    "  "
    (pretty tm.step)
  ==
::
::  +format-trace: render a trace to lines, eliding the middle beyond 200
::  lines (SPEC.md §6.3) unless the session fuel has been raised from the
::  default (env's type has no separate "fuel touched" flag, so this
::  reads that intent off the fuel value itself, which is an equivalent
::  observable in practice).
::
++  format-trace
  |=  [tr=(list trace-step) elide=?]
  ^-  (list tape)
  =/  lines  (turn tr render-trace-line)
  =/  n  (lent lines)
  ?.  &(elide (gth n 200))
    lines
  =/  hd  (scag 100 lines)
  =/  tl  (slag (sub n 100) lines)
  =/  elided  (sub n 200)
  %+  weld  hd
  [(weld "    … " (weld (render-ud elided) " steps elided …")) tl]
::
++  parse-ud
  |=  t=tape
  ^-  (unit @ud)
  ?~  t  ~
  ?.  (levy `tape`t |=(c=@ &((gte c '0') (lte c '9'))))  ~
  :-  ~
  =/  rest=tape  `tape`t
  =|  n=@ud
  |-
  ^-  @ud
  ?~  rest  n
  $(rest t.rest, n (add (mul n 10) (sub i.rest '0')))
::
::  --- small helpers for statement dispatch -------------------------------
::
++  starts-pct
  |=  p=@t
  ^-  ?
  =/  t=tape  (trip p)
  ?~  t  %.n
  =(i.t '%')
::
++  is-bind   |=(x=tok ?=(%bind -.x))
++  is-arrow  |=(x=tok ?=(%arrow -.x))
::
++  balanced
  |=  toks=(list tok)
  ^-  ?
  =/  opens=@ud  0
  =/  closes=@ud  0
  |-
  ?~  toks  =(opens closes)
  ?+  -.i.toks  $(toks t.toks)
    %lpar   $(toks t.toks, opens +(opens))
    %rpar   $(toks t.toks, closes +(closes))
  ==
::
++  find-top-level-idx
  |=  [toks=(list tok) mtch=$-(tok ?)]
  ^-  (unit @ud)
  =/  depth=@ud  0
  =/  i=@ud  0
  |-
  ^-  (unit @ud)
  ?~  toks  ~
  ?:  ?=(%lpar -.i.toks)  $(toks t.toks, depth +(depth), i +(i))
  ?:  ?=(%rpar -.i.toks)  $(toks t.toks, depth ?:(=(depth 0) 0 (dec depth)), i +(i))
  ?:  &(=(depth 0) (mtch i.toks))  `i
  $(toks t.toks, i +(i))
::
++  has-dups
  |=  l=(list @t)
  ^-  ?
  =/  seen=(set @t)  ~
  |-
  ^-  ?
  ?~  l  %.n
  ?:  (~(has in seen) i.l)  %.y
  $(l t.l, seen (~(put in seen) i.l))
::
++  find-shadowing-var
  |=  [session=env vars=(list @t) name=@t]
  ^-  (unit @t)
  |-
  ^-  (unit @t)
  ?~  vars  ~
  ?:  =(i.vars name)  $(vars t.vars)
  ?^  (lookup-comb session i.vars)  `i.vars
  $(vars t.vars)
::
++  join-sp
  |=  l=(list @t)
  ^-  tape
  ?~  l  ""
  ?~  t.l  (trip i.l)
  (weld (trip i.l) (weld " " (join-sp t.l)))
::
++  tape-lth
  |=  [a=tape b=tape]
  ^-  ?
  ?~  a  ?^(b %.y %.n)
  ?~  b  %.n
  ?:  =(i.a i.b)  $(a t.a, b t.b)
  (lth i.a i.b)
::
++  is-builtin-name
  |=  name=@t
  ^-  ?
  =/  rname  (resolve-name name)
  |((~(has by birds-map) rname) =(rname 'Θ'))
::
::  +toks-to-names: (list tok) -> (unit (list @t)), ~ if any element isn't
::  a plain %atom token. Written as its own recursive gate (rather than
::  inline ?=/levy checks at the call sites) so the %atom narrowing needed
::  to read .p off each token happens in one place, right next to the
::  ?= that establishes it -- reading .p after a levy/lent-only check at
::  the call site does not narrow and fails to compile (find-fork).
::
++  toks-to-names
  |=  toks=(list tok)
  ^-  (unit (list @t))
  ?~  toks  `~
  ?.  ?=(%atom -.i.toks)  ~
  =/  rest  (toks-to-names t.toks)
  ?~  rest  ~
  `[p.i.toks u.rest]
::
::  +tok-atom-name: same idea as +toks-to-names, for a single token.
::
++  tok-atom-name
  |=  t=tok
  ^-  (unit @t)
  ?.  ?=(%atom -.t)  ~
  `p.t
::
::  --- magics (SPEC-DESK.md §3: %ski %sk %fuel %defs %undef) -------------
::
++  magic-ski
  |=  [session=env rest=(list tok) to-sk=?]
  ^-  (each [out=(list tape) session=env] tape)
  ?~  rest  [%| "%ski expects an expression argument"]
  =/  parsed  (parse-expr-all rest)
  ?:  ?=(%| -.parsed)  parsed
  =/  ex  (expand session p.parsed ~ to-sk)
  ?:  ?=(%| -.ex)  ex
  [%& [(pretty p.ex)]~ session]
::
::  +magic-trace: %trace expr (v1.1, SPEC.md §6.3/§9) -- full step-by-step
::  reduction, one numbered line per contraction; fuel/size exhaustion is
::  still a warning line after the trace, never an error, same as a plain
::  expression statement.
::
++  magic-trace
  |=  [session=env rest=(list tok)]
  ^-  (each [out=(list tape) session=env] tape)
  ?~  rest  [%| "%trace expects an expression argument"]
  =/  parsed  (parse-expr-all rest)
  ?:  ?=(%| -.parsed)  parsed
  =/  res  (reduce-traced session p.parsed)
  =/  elide  =(fuel.session default-fuel)
  =/  lines  (format-trace trace.res elide)
  =/  warn=(list tape)
    ?:  =(status.res %fuel)
      [(weld "⚠ no normal form after " (weld (render-ud steps.res) " steps (fuel exhausted)"))]~
    ?:  =(status.res %size)
      :~  %+  weld  "⚠ term exceeded "
          (weld (render-ud size-cap) (weld " atoms after " (weld (render-ud steps.res) " steps")))
      ==
    ~
  [%& (weld lines warn) session]
::
++  magic-fuel
  |=  [session=env rest=(list tok)]
  ^-  (each [out=(list tape) session=env] tape)
  ?~  rest
    [%& [(weld "fuel (max_steps) = " (render-ud fuel.session))]~ session]
  ?.  =((lent rest) 1)
    [%| "%fuel expects a positive integer"]
  =/  nm  (toks-to-names rest)
  ?~  nm  [%| "%fuel expects a positive integer"]
  ?~  u.nm  [%| "%fuel expects a positive integer"]
  =/  raw  (trip i.u.nm)
  =/  n  (parse-ud raw)
  ?~  n
    [%| (weld "%fuel expects a positive integer, got '" (weld raw "'"))]
  ?:  =(u.n 0)
    [%| (weld "%fuel expects a positive integer, got '" (weld raw "'"))]
  [%& [(weld "fuel (max_steps) set to " (render-ud u.n))]~ session(fuel u.n)]
::
++  render-def
  |=  [p=@t q=def]
  ^-  tape
  ?-  -.q
    %alias  (weld (trip p) (weld " := " (pretty body.q)))
    %rule
      ;:  weld
        (trip p)  " "  (join-sp vars.q)  " -> "  (pretty rhs.q)
        "  (arity "  (render-ud arity.q)  ")"
      ==
  ==
::
++  def-lth
  |=  [a=[p=@t q=def] b=[p=@t q=def]]
  ^-  ?
  (tape-lth (trip p.a) (trip p.b))
::
++  magic-defs
  |=  [session=env rest=(list tok)]
  ^-  (each [out=(list tape) session=env] tape)
  =/  ks  (sort ~(tap by defs.session) def-lth)
  ?~  ks  [%& ["(no user definitions)"]~ session]
  [%& (turn ks render-def) session]
::
++  magic-undef
  |=  [session=env rest=(list tok)]
  ^-  (each [out=(list tape) session=env] tape)
  ?.  =((lent rest) 1)
    [%| "%undef expects a single name argument"]
  =/  nm  (toks-to-names rest)
  ?~  nm  [%| "%undef expects a single name argument"]
  ?~  u.nm  [%| "%undef expects a single name argument"]
  =/  name  i.u.nm
  ?.  (~(has by defs.session) name)
    [%| (weld "'" (weld (trip name) "' is not a user definition"))]
  [%& [(weld "undefined " (trip name))]~ session(defs (~(del by defs.session) name))]
::
++  run-magic
  |=  [session=env name=@t rest=(list tok)]
  ^-  (each [out=(list tape) session=env] tape)
  ?:  =(name '%ski')    (magic-ski session rest %.n)
  ?:  =(name '%sk')     (magic-ski session rest %.y)
  ?:  =(name '%trace')  (magic-trace session rest)
  ?:  =(name '%fuel')   (magic-fuel session rest)
  ?:  =(name '%defs')   (magic-defs session rest)
  ?:  =(name '%undef')  (magic-undef session rest)
  :-  %|
  %+  weld  "unknown magic '"
  %+  weld  (trip name)
  "'; available: %ski, %sk, %trace, %fuel, %defs, %undef"
::
::  --- statement handlers --------------------------------------------------
::
++  run-expr
  |=  [session=env toks=(list tok)]
  ^-  (each [out=(list tape) session=env] tape)
  =/  parsed  (parse-expr-all toks)
  ?:  ?=(%| -.parsed)  parsed
  =/  res  (reduce session p.parsed)
  =/  txt  (pretty rt.res)
  =/  suffix=tape
    ?:  &(=(status.res %normal) =(steps.res 0))
      "  [normal form]"
    ;:  weld
      "  ["  (render-ud steps.res)  " step"
      ?:(=(steps.res 1) "" "s")  "]"
    ==
  =/  line1  (weld txt suffix)
  =/  extra=(list tape)
    ?:  =(status.res %fuel)
      :~  (weld "⚠ no normal form after " (weld (render-ud steps.res) " steps (fuel exhausted)"))  ==
    ?:  =(status.res %size)
      :~  (weld "⚠ term exceeded " (weld (render-ud size-cap) (weld " atoms after " (weld (render-ud steps.res) " steps"))))  ==
    ~
  [%& (weld [line1]~ extra) session]
::
++  run-alias
  |=  [session=env toks=(list tok) idx=@ud]
  ^-  (each [out=(list tape) session=env] tape)
  =/  lhs  (scag idx toks)
  =/  rhs  (slag +(idx) toks)
  ?.  =((lent lhs) 1)
    [%| "alias left-hand side must be a single name"]
  =/  nm  (toks-to-names lhs)
  ?~  nm
    [%| "alias left-hand side must be a single name"]
  ?~  u.nm
    [%| "alias left-hand side must be a single name"]
  =/  name  i.u.nm
  ?~  rhs  [%| "alias has no body"]
  =/  parsed  (parse-expr-all rhs)
  ?:  ?=(%| -.parsed)  parsed
  ?:  (is-builtin-name name)
    [%| (weld "cannot shadow built-in '" (weld (trip name) "'"))]
  =/  env2  session(defs (~(put by defs.session) name [%alias p.parsed]))
  =/  conf  (weld "defined " (weld (trip name) (weld " := " (pretty p.parsed))))
  [%& [conf]~ env2]
::
++  run-rule
  |=  [session=env toks=(list tok) idx=@ud]
  ^-  (each [out=(list tape) session=env] tape)
  =/  lhs  (scag idx toks)
  =/  rhs  (slag +(idx) toks)
  ?.  (gte (lent lhs) 2)
    [%| "rule left-hand side must be NAME VAR+"]
  =/  allnames  (toks-to-names lhs)
  ?~  allnames
    [%| "rule left-hand side must be NAME VAR+"]
  ?~  u.allnames
    [%| "rule left-hand side must be NAME VAR+"]
  =/  name  i.u.allnames
  =/  vars  t.u.allnames
  ?~  rhs  [%| "rule has no body"]
  ?:  (is-builtin-name name)
    [%| (weld "cannot shadow built-in '" (weld (trip name) "'"))]
  ?:  (has-dups vars)
    [%| "duplicate variable in definition"]
  =/  bad  (find-shadowing-var session vars name)
  ?^  bad
    [%| (weld "variable '" (weld (trip u.bad) "' shadows a combinator"))]
  =/  parsed  (parse-expr-all rhs)
  ?:  ?=(%| -.parsed)  parsed
  =/  env2  session(defs (~(put by defs.session) name [%rule (lent vars) vars p.parsed]))
  =/  conf
    ;:  weld
      "defined "  (trip name)  " (arity "  (render-ud (lent vars))  "): "
      (trip name)  " "  (join-sp vars)  " -> "  (pretty p.parsed)
    ==
  [%& [conf]~ env2]
::
++  run-line
  |=  [session=env line=tape]
  ^-  (each [out=(list tape) session=env] tape)
  =/  lexed  (lex-line line)
  ?:  ?=(%| -.lexed)  lexed
  =/  toks  p.lexed
  ?~  toks  [%& ~ session]
  ?.  (balanced toks)  [%| "unbalanced parentheses"]
  =/  first-name  (tok-atom-name i.toks)
  =/  is-magic=?  ?~(first-name %.n (starts-pct u.first-name))
  ?:  is-magic
    (run-magic session (need first-name) t.toks)
  =/  bidx  (find-top-level-idx toks is-bind)
  =/  aidx  (find-top-level-idx toks is-arrow)
  ?:  &(?=(^ bidx) |(?=(~ aidx) (lth u.bidx u.aidx)))
    (run-alias session toks u.bidx)
  ?:  ?=(^ aidx)
    (run-rule session toks u.aidx)
  (run-expr session toks)
::
::  +run: the public entry point (SPEC-DESK.md §4) -- one statement in,
::  output lines + updated env out. Errors are lines prefixed "! " (north's
::  convention); warnings are prefixed "⚠ " and are produced as ordinary
::  output by ++run-expr, never as a crash/error here.
::
++  run
  |=  [session=env line=tape]
  ^-  [out=(list tape) session=env]
  =/  res  (run-line session line)
  ?-  -.res
    %|  [[(weld "! " p.res)]~ session]
    %&  p.res
  ==
--
