#!/usr/bin/env bash
# Hoon engine tests (SPEC-DESK.md §8) -- headless, via `urbit eval`.
# Run from repo root: bash tests/test-engine.sh
#
# Follows north master's tests/test-nock.sh pattern: pipe a `=>`-pipeline
# of Hoon source into `urbit eval` and grep the result.
#
# Since `/-`/`/+` Ford runes have no meaning outside a real Clay-backed
# desk, `urbit eval`'s raw text pipe can't process desk/lib/aviary.hoon's
# `/-  *aviary` line directly. We reconstruct what Ford would produce for
# a real install -- sur/aviary.hoon's core as the subject lib/aviary.hoon
# compiles against -- by chaining two `=>`: `=> sur-core => lib-core-sans-
# ford-line  test-expr`. (This chaining is also load-bearing for an
# unrelated reason: a `+$ term` mold that's directly self-referential
# through a `$%` union reproducibly fails to compile -- `%over` from the
# Hoon type-checker's `+dig` -- the moment it shares a `|%` core with any
# sibling arm; splitting sur and lib into separate `=>`-linked cores
# sidesteps it. See lib/aviary.hoon's header comment for the full story,
# including why `term`'s atom case ended up as a bare `$@(@t ...)` rather
# than a `[%atom name=@t]` tag.)
#
# Prefers one large Hoon expression (tests/test-engine-cases.hoon) that
# returns the list of failing case labels over many small `urbit eval`
# spawns, since each spawn costs real wall-clock seconds.

set -u

URBIT_BIN="${URBIT_BIN:-$HOME/bin/urbit}"
if [ ! -x "$URBIT_BIN" ]; then
  URBIT_BIN="$(command -v urbit || true)"
fi
if [ -z "$URBIT_BIN" ]; then
  echo "FAIL  no urbit binary found (set \$URBIT_BIN, or install to ~/bin/urbit or PATH)"
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUR="$ROOT/desk/sur/aviary.hoon"
LIB="$ROOT/desk/lib/aviary.hoon"
CASES="$ROOT/tests/test-engine-cases.hoon"

for f in "$SUR" "$LIB" "$CASES"; do
  if [ ! -f "$f" ]; then
    echo "FAIL  missing file: $f"
    exit 1
  fi
done

echo "=== Aviary Hoon engine tests (SPEC-DESK.md §8) ==="
echo "urbit: $URBIT_BIN"
echo

run_pipeline() {
  {
    printf '=>\n'
    cat "$SUR"
    printf '=>\n'
    grep -v '^/-' "$LIB"
    cat "$CASES"
  } | "$URBIT_BIN" eval 2>&1
}

RAW="$(run_pipeline)"

# Strip vere boot chatter and ANSI color codes, same as test-nock.sh.
CLEAN="$(printf '%s\n' "$RAW" \
  | grep -v '^loom:\|^lite:\|^eval (run):\|^eval:' \
  | sed 's/\x1b\[[0-9;]*m//g' \
  | tr -d '\r' \
  | sed '/^[[:space:]]*$/d')"

# A clean run's product is the failing-case list from test-engine-cases.hoon:
# `~` (or `<<>>`, seen for the statically-bunted empty case) if every case
# passed; otherwise a multi-line `~[ ... ]` noun dump of failing labels.
if [ "$CLEAN" = "~" ] || [ "$CLEAN" = "<<>>" ]; then
  echo "PASS  all §8 test groups (birds, laziness, full normalization,"
  echo "      definitions, expansion soundness, statement plumbing)"
  exit 0
fi

if printf '%s' "$RAW" | grep -qE 'bail: %(exit|term|over)|syntax error|nest-fail|mint-vain|mull-grow'; then
  echo "FAIL  Hoon did not compile/evaluate -- raw urbit eval output:"
  echo "$RAW"
  exit 1
fi

echo "FAIL  one or more §8 cases failed; failing-case labels:"
echo "$CLEAN"
exit 1
