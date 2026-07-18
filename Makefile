.PHONY: test test-hoon test-all

# Python test suite (aviary_kernel + tests/, including the Hoon registry
# cross-test in tests/test_hoon_registry.py -- SPEC-DESK.md §7).
test:
	python -m pytest tests/ -v

# Hoon engine tests (SPEC-DESK.md §8), headless via `urbit eval`.
# Override URBIT_BIN to point at a different binary; defaults to
# ~/bin/urbit, falling back to `urbit` on PATH (tests/test-engine.sh).
test-hoon:
	bash tests/test-engine.sh

# Both suites.
test-all: test test-hoon
