"""Точка входа: python -m depgrapher ..."""

import os
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from .cli import Config, ConfigError, parse_args, print_config


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    try:
        cfg = parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    except ConfigError as e:
        print(f"Ошибка параметров: {e}", file=sys.stderr)
        return 3

    print_config(cfg)

    from .aptrepo import RepoError
    from .graph import build_graph

    try:
        if cfg.mode == "url":
            from .aptrepo import fetch_url, parse_packages_index

            print(f"\n== Загрузка Packages-индекса: {cfg.source} ==")
            packages = parse_packages_index(fetch_url(cfg.source))
        else:
            from .testrepo import load_test_repo

            print(f"\n== Загрузка тестового репозитория: {cfg.source} ==")
            packages = load_test_repo(cfg.source)
        graph = build_graph(packages, cfg.package, cfg.version)
    except RepoError as e:
        print(f"Ошибка репозитория: {e}", file=sys.stderr)
        return 4
    except ValueError as e:
        print(f"Ошибка разбора репозитория: {e}", file=sys.stderr)
        return 4

    _print_graph(graph, len(packages))
    return _render_stage4(graph, cfg)


def _print_graph(graph, repo_size: int) -> None:
    """Вывод графа зависимостей (этап 3)."""
    print(f"\nВ репозитории пакетов: {repo_size}")
    print(f"\n== Пакет: {graph.nodes[graph.root_name]} ==")
    print("\n== Граф зависимостей (BFS с рекурсией) ==")
    print(f"Узлов: {len(graph.nodes)}, рёбер дерева: {len(graph.tree_edges)}, "
          f"обратных рёбер: {len(graph.cycle_edges)}")
    print("Порядок обхода (BFS): " + " -> ".join(graph.order))
    cycles = graph.describe_cycles()
    if cycles:
        print("\nОбнаружены циклические зависимости:")
        for i, c in enumerate(cycles, 1):
            print(f"{i}. " + " -> ".join(c))
    else:
        print("Циклических зависимостей: нет")
    if graph.unresolved:
        print("\nЗависимости, не удовлетворённые репозиторием:")
        for parent, dep in graph.unresolved:
            print(f"- {parent}: {dep}")


def _render_stage4(graph, cfg) -> int:
    """Этап 4: визуализация — ASCII-дерево (по запросу), PNG и SVG."""
    from .render import ascii_tree, render_png, render_svg

    if cfg.ascii == "tree":
        print("\n== ASCII-дерево зависимостей ==")
        print(ascii_tree(graph))

    print("\n== Визуализация графа ==")
    try:
        png, w, h = render_png(graph)
        svg = render_svg(graph)
    except Exception as e:
        print(f"Ошибка отрисовки: {e}", file=sys.stderr)
        return 5
    try:
        with open(cfg.output, "wb") as f:
            f.write(png)
        svg_path = os.path.splitext(cfg.output)[0] + ".svg"
        with open(svg_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
    except OSError as e:
        print(f"Ошибка записи файлов: {e}", file=sys.stderr)
        return 5
    print(f"PNG: {cfg.output} ({w}x{h} px, {len(png)} байт)")
    print(f"SVG: {svg_path} ({len(svg)} байт)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
