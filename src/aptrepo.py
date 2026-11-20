"""Загрузка и разбор Packages-индекса репозитория apt.

Используется только стандартная библиотека (urllib, gzip).
URL должен указывать на Packages-индекс (например,
http://archive.ubuntu.com/ubuntu/dists/noble/main/binary-amd64/Packages
или .../Packages.gz). Менеджеры пакетов и сторонние библиотеки
не используются.
"""

from __future__ import annotations

import gzip
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .deps import Dependency, parse_depends
from .versions import compare_versions

_DEFAULT_TIMEOUT = 60
_DECOMPRESSION_THRESHOLD = 2


class RepoError(Exception):
    """Ошибка работы с репозиторием (код выхода 4)."""


@dataclass
class Package:
    """Пакет из Packages-индекса."""

    name: str
    version: str
    architecture: str = ""
    depends: list = field(default_factory=list)
    provides: str = ""
    url: str = ""

    def __str__(self) -> str:
        return f"{self.name} {self.version}"


def fetch_url(url: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
    """Скачать текст из URL."""
    req = urllib.request.Request(
        url, headers={"User-Agent": "depgrapher/0.1 (apt-packages-fetcher)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            content_encoding = (
                    resp.headers.get("Content-Encoding") or "").lower()
    except urllib.error.HTTPError as e:
        raise RepoError(
            f"не удалось скачать {url}: HTTP {e.code} {e.reason}"
        ) from e
    except urllib.error.URLError as e:
        raise RepoError(f"не удалось скачать {url}: {e.reason}") from e
    except OSError as e:
        raise RepoError(f"не удалось скачать {url}: {e}") from e

    if "gzip" in content_encoding or (
            len(data) > _DECOMPRESSION_THRESHOLD and data[:2] == b"\x1f\x8b"):
        try:
            data = gzip.decompress(data)
        except OSError as e:
            raise RepoError(
                f"не удалось распаковать gzip-данные из {url}: {e}") from e
    return data.decode("utf-8", errors="replace")


def parse_packages_index(text: str) -> list:
    """Разобрать текст Packages-индекса в список Package."""
    packages = []
    stanza_lines: list = []
    for raw in text.splitlines():
        if raw.strip() == "":
            if stanza_lines:
                pkg = _parse_stanza(stanza_lines)
                if pkg:
                    packages.append(pkg)
                stanza_lines = []
        else:
            stanza_lines.append(raw)
    if stanza_lines:
        pkg = _parse_stanza(stanza_lines)
        if pkg:
            packages.append(pkg)
    return packages


def _parse_stanza(lines: list) -> "Package | None":
    fields: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        while i + 1 < len(lines) and lines[i + 1][:1] in (" ", "\t"):
            i += 1
            value += " " + lines[i].strip()
        if key in fields:
            fields[key] += " " + value
        else:
            fields[key] = value
        i += 1

    name = fields.get("package")
    version = fields.get("version")
    if not name or not version:
        return None
    try:
        depends = parse_depends(fields.get("depends", ""))
    except ValueError as e:
        raise RepoError(f"пакет {name} {version}: {e}") from e
    return Package(
        name=name,
        version=version,
        architecture=fields.get("architecture", ""),
        depends=depends,
        provides=fields.get("provides", ""),
    )


def _check_package(packages: list, name: str):
    """Выкинуть RepoError, если пакет не найден."""
    available = sorted({p.name for p in packages})

    close = [p for p in available if name.lower() in p or p in name.lower()]
    hint = f" (похожие: {', '.join(close[:5])})" if close else ""

    raise RepoError(
        f"пакет {name!r} не найден в репозитории{hint}; "
        f"всего пакетов: {len(available)}"
    )


def _select_exact_version(candidates: list, name: str, version: str):
    """Выбрать точную версию или выкинуть RepoError."""
    exact = [p for p in candidates if p.version == version]
    if exact: return exact[0]

    versions = sorted({p.version for p in candidates}, key=lambda v: v)
    raise RepoError(
        f"версия {version!r} пакета {name!r} не найдена в репозитории; "
        f"доступные версии: {', '.join(versions)}"
    )


def select_package(packages: list, name: str, version: "str | None") -> Package:
    """Выбрать пакет по имени и (опционально) точной версии."""
    candidates = [p for p in packages if p.name.lower() == name.lower()]

    if not candidates:
        _check_package(packages, name)

    if version is not None:
        return _select_exact_version(candidates, name, version)

    return _max_by_version(candidates)


def _max_by_version(candidates: list) -> Package:
    best = candidates[0]
    for p in candidates[1:]:
        if compare_versions(p.version, best.version) > 0:
            best = p
    return best
