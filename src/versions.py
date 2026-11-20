"""Разбор и сравнение версий в формате Debian (Debian Policy, секция 5.6.12).

Только стандартная библиотека.
Алгоритм сравнения — по Debian Policy, совместим с dpkg (vercmp):
- строка = [epoch:]upstream[-revision];
- upstream/revision разбираются на максимальные блоки цифр и
  нецифровых символов;
- числовые блоки сравниваются по численному значению;
- нецифровые блоки — лексикографически; '~' сортируется раньше
  всего (включая пустую строку), больше '~' — ниже версия;
- цифра всегда сортируется позже нецифрового символа;
- если одна строка закончилась, она ниже, кроме случая, когда в другой
  следующий символ — '~' ('~' сортируется раньше пустой строки).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION_RE = re.compile(
    r"^(?:(\d+):)?([0-9A-Za-z](?:[^-\r\n]*[0-9A-Za-z~.:+])?)"
    r"(?:-([0-9A-Za-z~.:+](?:[^\r\n]*[0-9A-Za-z~.:+])?))?$"
)


@dataclass(frozen=True)
class Version:
    epoch: int
    upstream: str
    revision: str

    @classmethod
    def parse(cls, text: str) -> "Version":
        m = _VERSION_RE.match(text.strip())
        if not m:
            raise ValueError(f"некорректная версия Debian: {text!r}")
        return cls(int(m.group(1) or 0), m.group(2) or "0", m.group(3) or "")

    def __str__(self) -> str:
        s = (f"{self.epoch}:" if self.epoch else "") + self.upstream
        if self.revision:
            s += f"-{self.revision}"
        return s


def _cmp_nondigit(r1: str, r2: str) -> int:
    """Сравнение блоков из нецифровых символов (с правилом '~')."""
    a = r1.lstrip("~")
    b = r2.lstrip("~")
    ta = len(r1) - len(a)
    tb = len(r2) - len(b)
    if a == b:
        if ta == tb:
            return 0
        return -1 if ta > tb else 1
    n = min(len(a), len(b))
    k = 0
    while k < n and a[k] == b[k]:
        k += 1
    if k < n:
        return -1 if a[k] < b[k] else 1
    return -1 if len(a) < len(b) else 1


def _run_end(s: str, i: int, is_digit: bool) -> int:
    """Вернуть индекс конца серии цифр/нецифр."""
    n = len(s)
    while i < n and s[i].isdigit() == is_digit:
        i += 1
    return i


def _cmp_int(a: str, b: str) -> int:
    """Сравнить две непустые цифровые серии."""
    x, y = int(a), int(b)
    return (x > y) - (x < y)


def _compare_runs(s1: str, i: int, s2: str, j: int):
    """Сравнить серии одного типа. Вернуть (result, i2, j2)."""
    digit = s1[i].isdigit()
    i2 = _run_end(s1, i, digit)
    j2 = _run_end(s2, j, digit)

    if digit:
        r = _cmp_int(s1[i:i2], s2[j:j2])
    else:
        r = _cmp_nondigit(s1[i:i2], s2[j:j2])

    return r, i2, j2


def _cmp_tail(a: str, b: str) -> int:
    """Сравнить остатки, когда хотя бы один пуст."""
    if not a:
        return 0 if not b else (1 if b[0] == "~" else -1)
    if not b:
        return -1 if a[0] == "~" else 1
    raise ValueError("_cmp_tail: оба остатка непусты")


def _cmp_part(s1: str, s2: str) -> int:
    """Сравнить две части версии (upstream или revision)."""
    i = j = 0
    n1, n2 = len(s1), len(s2)

    while i < n1 and j < n2:
        c1, c2 = s1[i], s2[j]

        if c1.isdigit() != c2.isdigit():
            return 1 if c1.isdigit() else -1

        r, i, j = _compare_runs(s1, i, s2, j)
        if r:
            return r

    return _cmp_tail(s1[i:], s2[j:])


def compare_versions(va: str, vb: str) -> int:
    """Сравнить две версии: -1 если va < vb, 0 если равны, +1 если va > vb."""
    a, b = Version.parse(va), Version.parse(vb)
    if a.epoch != b.epoch:
        return -1 if a.epoch < b.epoch else 1
    c = _cmp_part(a.upstream, b.upstream)
    if c:
        return c
    return _cmp_part(a.revision, b.revision)
