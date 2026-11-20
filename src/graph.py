"""Построение графа зависимостей (учёт транзитивности).

Граф строится алгоритмом BFS с рекурсией: рекурсивная функция
обрабатывает один «слой» (фронт) обхода в ширину и вызывает саму
себя для следующего слоя. Циклические зависимости обнаруживаются
по повторно посещаемым узлам и выносятся в отдельный список
(в дерево не включаются), поэтому обход на циклах завершается.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .aptrepo import Package, RepoError, select_package
from .deps import Dependency
from .versions import compare_versions


class GraphError(Exception):
    """Ошибка построения графа (код выхода 4)."""


@dataclass
class Graph:
    root_name: str
    nodes: dict = field(default_factory=dict)
    tree_edges: list = field(default_factory=list)
    cycle_edges: list = field(default_factory=list)
    unresolved: list = field(default_factory=list)
    order: list = field(default_factory=list)

    @property
    def has_cycles(self) -> bool:
        return bool(self.describe_cycles())

    def parents(self) -> dict:
        """Словарь child -> parent по рёбрам BFS-дерева."""
        return {child: parent for parent, child in self.tree_edges}

    def describe_cycles(self) -> list:
        """Восстановить циклы: список списков вида ['A','B','C','A'].

        Обратное ребро (u -> v) образует цикл, только если v является
        предком u в BFS-дереве; остальные рёбра к уже посещённым узлам
        (конфлюэнции/«алмазы») циклом не считаются.
        """
        parent = self.parents()
        cycles = []
        for u, v in self.cycle_edges:
            chain = [u]
            cur = u
            seen = {u}
            while cur != v:
                cur = parent.get(cur)
                if cur is None or cur in seen:
                    break
                seen.add(cur)
                chain.append(cur)
            if chain[-1] == v:
                cycles.append(chain[::-1] + [v])
        return cycles


def _resolve_dependency(index: dict, dep: Dependency) -> "Package | None":
    """Выбрать пакет, удовлетворяющий зависимости (самая высокая версия)."""
    candidates = [
        p for p in index.get(dep.name.lower(), []) if
        dep.satisfied_by(p.version)
    ]
    if not candidates:
        return None
    best = candidates[0]
    for p in candidates[1:]:
        if compare_versions(p.version, best.version) > 0:
            best = p
    return best


def build_graph(packages: list, root_name: str,
                root_version: "str | None") -> Graph:
    """Построить граф зависимостей от пакета root_name (BFS с рекурсией).
    `packages` — список пакетов репозитория (реального или тестового).
    """
    root = select_package(packages, root_name, root_version)
    index: dict = {}
    for p in packages: index.setdefault(p.name.lower(), []).append(p)

    graph = Graph(root_name=root.name)
    graph.nodes[root.name] = root
    graph.order.append(root.name)

    def _choose_alternative(alts: list):
        for dep in alts:
            pkg = _resolve_dependency(index, dep)
            if pkg is not None: return pkg, dep
        return None, alts[0]

    def _bfs_layer(frontier: list) -> None:
        next_frontier = []
        for name in frontier:
            pkg = graph.nodes[name]
            for alts in pkg.depends:
                child, chosen_dep = _choose_alternative(alts)
                if child is None:
                    graph.unresolved.append((name, chosen_dep))
                    continue
                cname = child.name
                if cname not in graph.nodes:
                    graph.nodes[cname] = child
                    graph.tree_edges.append((name, cname))
                    graph.order.append(cname)
                    next_frontier.append(cname)
                elif (name, cname) not in graph.cycle_edges:
                    graph.cycle_edges.append((name, cname))
        if next_frontier: _bfs_layer(next_frontier)

    _bfs_layer([root.name])
    return graph
