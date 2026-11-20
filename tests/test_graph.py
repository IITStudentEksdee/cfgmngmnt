"""Тесты построения графа зависимостей (BFS с рекурсией, циклы)."""

import unittest

from src.graph import Package, build_graph


def p(name, version, *deps):
    """Сокращение: deps — строки вида 'x' или 'x(>=1.0)' или ('a|b')."""
    from src.deps import parse_depends

    parsed = []
    for d in deps:
        parsed.extend(parse_depends(d))
    return Package(name=name, version=version, depends=parsed)


class TestGraph(unittest.TestCase):
    def test_chain(self):
        pkgs = [
            p("A", "1.0", "B"),
            p("B", "1.0", "C"),
            p("C", "1.0", "D"),
            p("D", "1.0"),
        ]
        g = build_graph(pkgs, "A", None)
        self.assertEqual(list(g.nodes), ["A", "B", "C", "D"])
        self.assertEqual(g.tree_edges, [("A", "B"), ("B", "C"), ("C", "D")])
        self.assertEqual(g.cycle_edges, [])
        self.assertFalse(g.has_cycles)
        self.assertEqual(g.order, ["A", "B", "C", "D"])

    def test_cycle(self):
        pkgs = [
            p("A", "1.0", "B, D"),
            p("B", "1.0", "C"),
            p("C", "1.0", "A"),
            p("D", "1.0"),
        ]
        g = build_graph(pkgs, "A", None)
        self.assertEqual(sorted(g.nodes), ["A", "B", "C", "D"])
        self.assertTrue(g.has_cycles)
        self.assertEqual(g.describe_cycles(), [["A", "B", "C", "A"]])

    def test_self_loop(self):
        pkgs = [p("E", "1.0", "E")]
        g = build_graph(pkgs, "E", None)
        self.assertEqual(g.describe_cycles(), [["E", "E"]])

    def test_diamond_not_a_cycle(self):
        pkgs = [
            p("A", "1.0", "B", "C"),
            p("B", "1.0", "D"),
            p("C", "1.0", "D"),
            p("D", "1.0"),
        ]
        g = build_graph(pkgs, "A", None)
        self.assertEqual(sorted(g.nodes), ["A", "B", "C", "D"])
        self.assertEqual(g.describe_cycles(), [])

    def test_alternatives(self):
        pkgs = [
            p("A", "1.0", "B|C"),
            p("B", "2.0", "D(>=1.0)"),
            p("C", "2.0", "D(>=1.0)"),
            p("D", "1.0"),
            p("D", "0.9"),
        ]
        g = build_graph(pkgs, "A", None)
        self.assertIn("B", g.nodes)
        self.assertNotIn("C", g.nodes)
        self.assertEqual(g.nodes["D"].version, "1.0")

    def test_version_constraint(self):
        pkgs = [
            p("A", "1.0", "B(>=1.0)"),
            p("B", "2.0"),
            p("B", "1.0"),
            p("B", "0.9"),
        ]
        g = build_graph(pkgs, "A", None)
        self.assertEqual(g.nodes["B"].version, "2.0")

    def test_unresolvable(self):
        pkgs = [p("A", "1.0", "X(>=2.0)"), p("X", "1.0")]
        g = build_graph(pkgs, "A", None)
        self.assertEqual(len(g.unresolved), 1)
        self.assertEqual(g.unresolved[0][0], "A")
        self.assertNotIn("X", g.nodes)

    def test_root_version_selection(self):
        pkgs = [
            p("A", "1.0", "B"),
            p("A", "0.5"),
            p("B", "1.0"),
        ]
        g = build_graph(pkgs, "A", "0.5")
        self.assertEqual(g.nodes["A"].version, "0.5")


if __name__ == "__main__":
    unittest.main()
