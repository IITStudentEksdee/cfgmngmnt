"""Тесты визуализации (этап 4): ASCII-дерево, SVG, PNG (struct + zlib)."""

import unittest
from xml.etree import ElementTree

from src import render
from src.aptrepo import Package
from src.deps import parse_depends
from src.graph import build_graph


def _p(name, version, *dep_specs):
    depends = []
    for spec in dep_specs:
        depends.extend(parse_depends(spec))
    return Package(name=name, version=version, depends=depends)


class RenderTests(unittest.TestCase):
    def _chain(self):
        return build_graph(
            [_p("A", "1.0", "B"), _p("B", "1.0", "C"),
             _p("C", "1.0", "D"), _p("D", "1.0")],
            "A", None)

    def _cycle(self):
        return build_graph(
            [_p("A", "1.0", "B, D"), _p("B", "1.0", "C"),
             _p("C", "1.0", "A"), _p("D", "1.0")],
            "A", None)

    def test_ascii_tree_chain(self):
        out = render.ascii_tree(self._chain())
        lines = out.splitlines()
        self.assertEqual(lines[0], "A 1.0")
        self.assertIn("B 1.0", lines[1])
        self.assertIn("C 1.0", lines[2])
        self.assertIn("D 1.0", lines[3])
        self.assertIn("└── ", out)
        self.assertNotIn("[цикл]", out)

    def test_ascii_tree_cycle_marked(self):
        g = self._cycle()
        out = render.ascii_tree(g)
        self.assertIn("[цикл] A -> B -> C -> A", out)
        tree_part = [l for l in out.split("[цикл]")[0].splitlines() if l]
        self.assertEqual(len(tree_part), 4)

    def test_png_roundtrip(self):
        g = self._chain()
        png, w, h = render.render_png(g)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        dw, dh, p0 = render.decode_png_pixels(png)
        self.assertEqual((dw, dh), (w, h))
        self.assertEqual(p0, render.BG)

    def test_png_node_pixels(self):
        g = self._chain()
        png, w, h = render.render_png(g)
        pos, dims = render.layout(g)
        x, y = pos["A"]
        self.assertEqual(render.pixel_at(png, x + 4, y + 4), render.ROOT_FILL)
        x, y = pos["D"]
        self.assertEqual(render.pixel_at(png, x + 4, y + 4), render.NODE_FILL)
        self.assertEqual(render.pixel_at(png, x - 2, y), render.NODE_EDGE)

    def test_png_has_content(self):
        png, w, h = render.render_png(self._chain())
        _, _, raw = render.decode_png(png)
        bg = bytes(render.BG) * 3
        self.assertNotEqual(raw[1:], bg * (w * h))

    def test_png_selfloop_renders(self):
        g = build_graph(
            [_p("A", "1.0", "B"), _p("B", "2.0", "E"),
             _p("C", "1.0", "B(>=1.0), D"), _p("D", "1.0"),
             _p("E", "1.0", "E")],
            "A", None)
        png, w, h = render.render_png(g)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertGreater(w, 100)
        self.assertGreater(h, 100)

    def test_encode_png_single_pixel(self):
        buf = bytes((255, 0, 0)) * 4
        data = render.encode_png(2, 2, buf)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(render.pixel_at(data, 1, 1), (255, 0, 0))

    def test_svg_parses(self):
        g = self._cycle()
        svg = render.render_svg(g)
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        texts = [el.text or "" for el in root.iter(
            "{http://www.w3.org/2000/svg}text")]
        self.assertIn("A", texts)
        self.assertIn("B", texts)
        self.assertIn("C", texts)

    def test_layout_depths(self):
        g = self._chain()
        pos, dims = render.layout(g)
        xs = {x for x, y in pos.values()}
        self.assertEqual(len(xs), 4)
        self.assertEqual(set(pos), {"A", "B", "C", "D"})


if __name__ == "__main__":
    unittest.main()
