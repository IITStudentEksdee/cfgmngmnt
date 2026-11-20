"""Разбор полей Depends/Recommends (apt, формат Debian) и проверка ограничений.

Пример поля:  libc6 (>= 2.34), libfoo | libbar, zlib1g (>= 1.2.11)
- элементы разделяются запятыми;
- внутри элемента альтернативы разделяются '|' (достаточно установки одной);
- у атомарной зависимости может быть ограничение версии.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .versions import Version, compare_versions
from .versions import _cmp_part as _cmp_part_impl

_ATOM_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9+][A-Za-z0-9+~.:-]*?)\s*(?:"
    r"\(\s*(?P<op><<|<=|!=|>=|>>|<|>|=)\s*(?P<version>[^()\s]+)\s*\))?\s*$"
)
_OPERATOR_MAP = {
    "=": lambda c: c == 0,
    "!=": lambda c: c != 0,
    "<": lambda c: c < 0,
    "<=": lambda c: c <= 0,
    ">": lambda c: c > 0,
    ">=": lambda c: c >= 0,
    ">>": lambda c: c > 0,
    "<<": lambda c: c < 0,
}


@dataclass(frozen=True)
class Dependency:
    """Атомарная зависимость: имя пакета (и опциональное ограничение версии)."""

    name: str
    operator: str = ""
    version: str = ""

    def satisfied_by(self, version: str) -> bool:
        """Выполняется ли ограничение версией `version`."""
        op = self.operator
        if not op: return True

        predicate = _OPERATOR_MAP.get(op)
        if predicate is None:
            raise ValueError(f"неизвестный оператор {op!r}")

        if op in ("<<", ">>"):
            a = Version.parse(version)
            b = Version.parse(self.version)
            c = _cmp_part_impl(a.upstream, b.upstream)
            if c == 0:
                c = _cmp_part_impl(a.revision, b.revision)
        else:
            c = compare_versions(version, self.version)

        return predicate(c)

    def __str__(self) -> str:
        if self.operator:
            return f"{self.name} ({self.operator} {self.version})"
        return self.name


def _split_top_level(value: str, sep: str) -> list:
    parts = []
    buf = []
    depth = 0
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def parse_depends(value: str) -> list:
    """Разобрать значение поля в список альтернатив: list[list[Dependency]]."""
    if not value or not value.strip():
        return []
    alternatives = []
    for item in _split_top_level(value, ","):
        alts = []
        for atom in _split_top_level(item, "|"):
            m = _ATOM_RE.match(atom)
            if not m:
                raise ValueError(f"не удалось разобрать зависимость: {atom!r}")
            alts.append(Dependency(
                name=m.group("name"),
                operator=m.group("op") or "",
                version=m.group("version") or "",
            ))
        alternatives.append(alts)
    return alternatives


def format_depends(alternatives: list) -> str:
    """Обратно в строку (для вывода)."""
    items = []
    for alts in alternatives:
        items.append(" | ".join(str(d) for d in alts))
    return ", ".join(items)
