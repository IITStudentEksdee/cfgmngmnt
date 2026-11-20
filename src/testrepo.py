"""Разбор файла тестового репозитория (режим --mode file).

Формат (один пакет на строку):

    ИМЯ ВЕРСИЯ: ЗАВИСИМОСТЬ1, ЗАВИСИМОСТЬ2, ...

- пакеты называются большими латинскими буквами (допускаются цифры);
- версии — в формате Debian (например 1.0, 2.0-1);
- после двоеточия — зависимости: имя, имя с ограничением версии
  в скобках `B(>=2.0)`, альтернативы через `|`;
- строки, начинающиеся с `#`, и пустые строки игнорируются.
"""

from __future__ import annotations

import re

from .aptrepo import Package, RepoError
from .deps import parse_depends
from .versions import Version

_LINE_RE = re.compile(r"^\s*([A-Z][A-Z0-9]*)\s+(\S+)(?:\s*:\s*(.*?))?\s*$")


def parse_test_repo(text: str, path: str = "<file>") -> list:
    """Разобрать текст тестового репозитория в список Package."""
    packages = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            raise RepoError(
                f"{path}:{lineno}: некорректная строка {line!r}; "
                "ожидалось: ИМЯ ВЕРСИЯ: ЗАВИСИМОСТЬ1, ЗАВИСИМОСТЬ2"
            )
        name, version, dep_spec = m.group(1), m.group(2), m.group(3)
        try:
            Version.parse(version)
        except ValueError as e:
            raise RepoError(f"{path}:{lineno}: {e}") from e
        try:
            depends = parse_depends(dep_spec) if dep_spec else []
        except ValueError as e:
            raise RepoError(f"{path}:{lineno}: {e}") from e
        packages.append(Package(name=name, version=version, depends=depends))
    return packages


def load_test_repo(path: str) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise RepoError(
            f"не удалось прочитать файл тестового репозитория {path}: {e}")
    return parse_test_repo(text, path)
