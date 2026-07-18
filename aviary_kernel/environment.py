"""Session environment: unifies the built-in bird registry and
user/session definitions (SPEC.md §7) behind one lookup used by the
reducer and the basis-expander, so a symbol defined after a term was
entered still takes effect (§3), and so built-in aliases like Θ get the
same shadow-protection as built-in birds.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .birds import BIRDS, BY_NAME, Bird, BUILTIN_ALIASES, BUILTIN_ALIAS_KEYS
from .terms import Atom, App, Term, free_vars, pretty as _pretty


class DefinitionError(Exception):
    pass


@dataclass(frozen=True)
class Combinator:
    """Normalized view over a Bird or a Definition, used by reduce.py and
    abstraction.py so they don't need to know which kind they've got."""
    name: str
    arity: int
    formals: tuple[str, ...]
    body: Term            # rule RHS (arity>0) or full alias body (arity==0)
    ski: Term | None       # explicit override (only Y)
    is_builtin: bool
    is_alias: bool          # arity == 0


@dataclass
class Definition:
    name: str
    arity: int
    formals: tuple[str, ...]
    body: Term
    is_alias: bool
    builtin: bool = False
    source_text: str = ""


class Environment:
    """Holds session-scoped user definitions plus session preferences
    (fuel, size, ascii/unicode display, fuel-changed flag for trace
    elision). Built-in birds are immutable module data (birds.py)."""

    def __init__(self) -> None:
        self.definitions: dict[str, Definition] = {}
        self._alias_keys: dict[str, str] = {}  # alias-name -> canonical def name
        self.max_steps: int = 10_000
        self.max_size: int = 100_000
        self.fuel_changed: bool = False
        self.size_changed: bool = False
        self.ascii_mode: bool = False
        self.expansion_cache: dict[str, Term] = {}
        self._install_builtin_aliases()

    def _install_builtin_aliases(self) -> None:
        for canon, (dname, body) in BUILTIN_ALIASES.items():
            self.definitions[canon] = Definition(
                name=dname, arity=0, formals=(), body=body,
                is_alias=True, builtin=True, source_text=f"{dname} := U U",
            )
        for alias_key, target in BUILTIN_ALIAS_KEYS.items():
            if alias_key != target:
                self._alias_keys[alias_key] = target

    # --- lookup -------------------------------------------------------

    def lookup(self, name: str) -> Combinator | None:
        bird = BY_NAME.get(name)
        if bird is not None:
            return Combinator(
                name=bird.name, arity=bird.arity, formals=bird.formals,
                body=bird.rule, ski=bird.ski, is_builtin=True,
                is_alias=False,
            )
        canon = self._alias_keys.get(name, name)
        d = self.definitions.get(canon)
        if d is not None:
            return Combinator(
                name=d.name, arity=d.arity, formals=d.formals, body=d.body,
                ski=None, is_builtin=d.builtin, is_alias=d.is_alias,
            )
        return None

    def is_builtin_name(self, name: str) -> bool:
        if name in BY_NAME:
            return True
        canon = self._alias_keys.get(name, name)
        d = self.definitions.get(canon)
        return bool(d and d.builtin)

    # --- definitions ----------------------------------------------------

    def define_alias(self, name: str, body: Term, source_text: str = "") -> Definition:
        self._check_shadow(name)
        d = Definition(name=name, arity=0, formals=(), body=body,
                        is_alias=True, builtin=False, source_text=source_text)
        self.definitions[name] = d
        self.expansion_cache.clear()
        return d

    def define_rule(self, name: str, formals: tuple[str, ...], body: Term,
                     source_text: str = "") -> Definition:
        self._check_shadow(name)
        seen: set[str] = set()
        for v in formals:
            if v in seen:
                raise DefinitionError(f"duplicate variable '{v}' in definition of '{name}'")
            seen.add(v)
            existing = self.lookup(v)
            if existing is not None and v != name:
                raise DefinitionError(f"variable '{v}' shadows a combinator")
        # Check every atom in body is a formal, a defined combinator, the
        # name itself (recursion), or a free symbol (allowed, informational).
        free_syms: set[str] = set()
        for atom_name in free_vars(body):
            if atom_name in formals:
                continue
            if atom_name == name:
                continue  # recursion allowed
            if self.lookup(atom_name) is not None:
                continue
            free_syms.add(atom_name)
        d = Definition(name=name, arity=len(formals), formals=tuple(formals),
                        body=body, is_alias=False, builtin=False,
                        source_text=source_text)
        self.definitions[name] = d
        self.expansion_cache.clear()
        d._free_syms = free_syms  # type: ignore[attr-defined]
        return d

    def _check_shadow(self, name: str) -> None:
        if name in BY_NAME:
            raise DefinitionError(f"cannot shadow built-in '{name}'")
        existing = self.definitions.get(name)
        if existing is not None and existing.builtin:
            raise DefinitionError(f"cannot shadow built-in '{name}'")

    def undef(self, name: str) -> Definition:
        d = self.definitions.get(name)
        if d is None or d.builtin:
            raise DefinitionError(f"'{name}' is not a user definition")
        del self.definitions[name]
        self.expansion_cache.clear()
        return d

    def user_definitions(self) -> list[Definition]:
        return [d for d in self.definitions.values() if not d.builtin]

    # --- display --------------------------------------------------------

    def display_name(self, name: str) -> str:
        """Registry names get the session's script preference (Unicode
        subscripts by default, ASCII under %ascii on); free variables and
        user definitions are shown exactly as their canonical name,
        never transformed (SPEC.md §4.3)."""
        bird = BY_NAME.get(name)
        if bird is not None:
            return bird.name if self.ascii_mode else bird.display
        return name

    def pretty(self, term: Term) -> str:
        return _pretty(term, display=self.display_name)
