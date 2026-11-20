"""Парсинг и валидация параметров командной строки.

Все настраиваемые пользователем параметры:
  --package   имя анализируемого пакета
  --source    URL репозитория либо путь к файлу тестового репозитория
  --mode      режим работы с тестовым репозиторием: url | file
  --version   версия пакета
  --output    имя файла с изображением графа (PNG)
  --ascii     режим вывода зависимостей в виде ASCII-дерева: off | tree
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, fields
from typing import Optional

DEBIAN_PACKAGE_RE = re.compile(r"^[a-z][a-z0-9+]*(\.[a-z0-9+]*)*$")

TEST_PACKAGE_RE = re.compile(r"^[A-Z][A-Z0-9]*$")

DEBIAN_VERSION_RE = re.compile(
    r"^(?P<epoch>\d+:)?"
    r"(?P<upstream>[0-9A-Za-z](?:[0-9A-Za-z.:+~-]*[0-9A-Za-z])?)"
    r"(?:-(?P<revision>[0-9A-Za-z](?:[0-9A-Za-z.+~-]*[0-9A-Za-z])?))?$"
)

PNG_EXT = ".png"


class ParameterError(Exception):
    """Ошибка значения параметра командной строки (код выхода 2)."""


class ConfigError(Exception):
    """Ошибка согласованности параметров (код выхода 3)."""


@dataclass
class Config:
    package: str
    source: str
    mode: str
    version: Optional[str]
    output: str
    ascii: str


def _fail(msg: str) -> "argparse.ArgumentTypeError":
    raise argparse.ArgumentTypeError(msg)


def v_package(value: str) -> str:
    v = value.strip()
    if not v:
        raise _fail("имя пакета не может быть пустым")
    if not re.match(r"^[A-Za-z][A-Za-z0-9+.~-]*$", v):
        raise _fail(
            f"некорректное имя пакета {value!r}: допустимы латинские буквы, "
            "цифры и символы '+', '.', '-'; имя не может начинаться с цифры"
        )
    return v


def v_source(value: str) -> str:
    v = value.strip()
    if not v:
        raise _fail("адрес источника не может быть пустым")
    return v


def v_mode(value: str) -> str:
    v = value.strip().lower()
    if v not in ("url", "file"):
        raise _fail("режим должен быть 'url' (реальный репозиторий apt) "
                    "или 'file' (тестовый репозиторий)")
    return v


def v_version(value: str) -> str:
    v = value.strip()
    if not DEBIAN_VERSION_RE.match(v):
        raise _fail(
            f"некорректная версия {value!r}: ожидается формат Debian [эпоха:]"
            f"верхнепотоковая[-ревизия], например 1.2.3-4 или 1:2.0-1ubuntu2"
        )
    return v


def v_output(value: str) -> str:
    v = value.strip()
    if not v:
        raise _fail("имя выходного файла не может быть пустым")
    if not v.lower().endswith(PNG_EXT):
        raise _fail(f"имя файла изображения должно "
                    f"оканчиваться на {PNG_EXT}: {value!r}")
    return v


def v_ascii(value: str) -> str:
    v = value.strip().lower()
    if v not in ("off", "tree"):
        raise _fail("режим ASCII-дерева должен быть 'off' или 'tree'")
    return v


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="depgrapher",
        description="Построение и визуализация графа зависимостей пакета "
                    "(формат apt) без использования менеджеров пакетов."
    )
    p.add_argument("-p", "--package", type=v_package, required=True,
                   metavar="NAME",
                   help="имя анализируемого пакета")
    p.add_argument("-s", "--source", type=v_source, required=True,
                   metavar="URL_OR_PATH",
                   help="URL-адрес репозитория (Packages-индекс) либо "
                        "путь к файлу тестового репозитория")
    p.add_argument("-m", "--mode", type=v_mode, default="url",
                   help="режим работы с репозиторием: url — реальный "
                        "apt-репозиторий, file — тестовый репозиторий из файла "
                        "(по умолчанию: url)")
    p.add_argument("-v", "--version", type=v_version, default=None,
                   metavar="VERSION",
                   help="версия пакета (формат Debian), по умолчанию — "
                        "последняя в репозитории")
    p.add_argument("-o", "--output", type=v_output,
                   default="dependency-graph.png", metavar="FILE.png",
                   help="имя файла с изображением графа (по умолчанию: "
                        "dependency-graph.png)")
    p.add_argument("-a", "--ascii", type=v_ascii, default="off", dest="ascii",
                   help="режим вывода зависимостей в виде ASCII-дерева: "
                        "off | tree (по умолчанию: off)")
    return p


def validate(cfg: Config) -> None:
    """Согласованность параметров (взаимозависимости между опциями)."""
    if cfg.mode == "url":
        if not re.match(r"^https?://", cfg.source, re.I):
            raise ConfigError(
                f"--source={cfg.source!r} не является URL; в режиме 'url' "
                f"ожидается http(s)-ссылка на Packages-индекс (например, "
                f"http://archive.ubuntu.com/ubuntu/dists/noble/main/"
                f"binary-amd64/Packages)"
            )
        if not DEBIAN_PACKAGE_RE.match(cfg.package):
            raise ConfigError(
                f"пакет {cfg.package!r} не соответствует именованию apt "
                "(строчные латинские буквы, цифры, '+', '.', '-') — "
                "проверьте опцию --package или используйте --mode file"
            )
    else:
        if cfg.source.lower().startswith(("http://", "https://")):
            raise ConfigError(
                f"--mode file указан, но --source={cfg.source!r} является URL; "
                "ожидается путь к файлу тестового репозитория"
            )
        if not os.path.isfile(cfg.source):
            raise ConfigError(
                f"файл тестового репозитория не найден или недоступен: "
                f"{cfg.source!r} (проверьте опцию --source)"
            )
        if not TEST_PACKAGE_RE.match(cfg.package):
            raise ConfigError(
                f"в тестовом репозитории пакеты называются большими латинскими "
                f"буквами: {cfg.package!r} не подходит (например 'A', 'BC2')"
            )
    out = os.path.dirname(os.path.abspath(cfg.output))
    if out and not os.path.isdir(out):
        raise ConfigError(f"каталог выходного файла не существует: {out}")


def parse_args(argv: Optional[list] = None) -> Config:
    args = build_parser().parse_args(argv)
    cfg = Config(
        package=args.package,
        source=args.source,
        mode=args.mode,
        version=args.version,
        output=args.output,
        ascii=args.ascii,
    )
    validate(cfg)
    return cfg


def print_config(cfg: Config) -> None:
    """Этап 1: вывод всех настраиваемых параметров в формате ключ-значение."""
    print("== Параметры запуска ==")
    for f in fields(Config):
        print(f"{f.name} = {getattr(cfg, f.name)}")
