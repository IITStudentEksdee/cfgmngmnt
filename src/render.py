"""Визуализация графа зависимостей (этап 4).

Три формата вывода, только стандартная библиотека Python:

* ``ascii_tree(graph)`` — текстовое ASCII-дерево зависимостей;
* ``render_svg(graph)`` — векторная SVG-картинка;
* ``render_png(graph)`` — растровая PNG, кодируемая собственным
  растреризатором (структурированный PNG-кодировщик на ``struct`` +
  ``zlib``, шрифт — 5x7 растровые глифы, целочисленное масштабирование).

Внешние библиотеки (Cairo, PIL и т.п.) не используются.
"""

from __future__ import annotations

import math
import struct
import zlib
from xml.sax.saxutils import escape as _xml_escape

_RAW_FONT = {
    "A": "01110 10001 10001 11111 10001 10001 10001",
    "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110",
    "D": "11100 10010 10001 10001 10001 10010 11100",
    "E": "11111 10000 10000 11110 10000 10000 11111",
    "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111",
    "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110",
    "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001",
    "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001",
    "N": "10001 10001 11001 10101 10011 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110",
    "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10101 10010 10100 01010",
    "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110",
    "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110",
    "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 10101 01010",
    "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100",
    "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10001 10011 10101 11001 10001 01110",
    "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00110 01000 10000 11111",
    "3": "01110 10001 00001 00110 00001 10001 01110",
    "4": "00010 00110 01010 10010 11111 00010 00010",
    "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "01110 10000 10000 11110 10001 10001 01110",
    "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110",
    "9": "01110 10001 10001 01111 00001 00001 01110",
    " ": "00000 00000 00000 00000 00000 00000 00000",
    "-": "00000 00000 00000 01110 00000 00000 00000",
    "_": "00000 00000 00000 00000 00000 00000 11111",
    ".": "00000 00000 00000 00000 00000 00100 00100",
    ",": "00000 00000 00000 00000 00100 00100 01000",
    ":": "00000 00100 00100 00000 00100 00100 00000",
    ";": "00000 00100 00100 00000 00100 00100 01000",
    "(": "00010 00100 01000 01000 01000 00100 00010",
    ")": "01000 00100 00010 00010 00010 00100 01000",
    "/": "00001 00001 00010 00100 01000 10000 10000",
    "+": "00000 00100 00100 11111 00100 00100 00000",
    "=": "00000 00000 11111 00000 11111 00000 00000",
    ">": "10000 01000 00100 00010 00100 01000 10000",
    "<": "00001 00010 00100 01000 00100 00010 00001",
    "|": "00100 00100 00100 00100 00100 00100 00100",
    "[": "00111 00100 00100 00100 00100 00100 00111",
    "]": "11000 00100 00100 00100 00100 00100 11000",
    "*": "00000 10101 01110 00100 01110 10101 00000",
    "!": "00100 00100 00100 00100 00100 00000 00100",
    "?": "01110 10001 00001 00110 00100 00000 00100",
    "'": "00100 00100 01000 00000 00000 00000 00000",
    '"': "01010 01010 01010 00000 00000 00000 00000",
    "#": "01010 01010 11111 01010 11111 01010 01010",
    "%": "11001 00010 00010 00100 01000 01000 10001",
    "&": "01000 10010 10010 01000 10101 10010 01001",
    "~": "00000 00000 00000 10000 01010 00100 00000",
}

FONT = {ch: [int(row, 2) for row in spec.split()] for ch, spec in
        _RAW_FONT.items()}
_FONT_W = 5
_FONT_H = 7


def text_width(s: str, scale: int = 1) -> int:
    """Ширина строки в пикселях (6 ячеек на глиф, без хвостового зазора)."""
    if not s:
        return 0
    return (len(s) * 6 - 1) * scale


class Canvas:
    """Простая RGB-поверхность с примитивами (rect, line, text)."""
    def __init__(self, w: int, h: int, bg: tuple):
        self.w = w
        self.h = h
        self.buf = bytearray(bytes(bg) * (w * h))

    def set(self, x: int, y: int, c: tuple) -> None:
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def rect(self, x: int, y: int, w: int, h: int, c: tuple) -> None:
        x0, y0 = int(x), int(y)
        for yy in range(y0, y0 + int(h)):
            for xx in range(x0, x0 + int(w)):
                self.set(xx, yy, c)

    def line(self, x0: int, y0: int, x1: int, y1: int, c: tuple,
             thick: int = 2) -> None:
        steps = int(max(abs(x1 - x0), abs(y1 - y0)))
        if steps == 0:
            steps = 1
        r = max(1, thick // 2)
        for i in range(steps + 1):
            t = i / steps
            self.rect(
                x0 + (x1 - x0) * t - r, y0 + (y1 - y0) * t - r, 2 * r, 2 * r, c
            )

    def text(self, x: int, y: int, s: str, c: tuple, scale: int = 1) -> None:
        px = x
        for ch in s:
            g = FONT.get(ch.upper())
            if g is None:
                g = FONT.get(ch)
            if g is None:
                g = FONT["#"]
            for row in range(_FONT_H):
                bits = g[row]
                for col in range(_FONT_W):
                    if bits & (1 << (_FONT_W - 1 - col)):
                        self.rect(px + col * scale, y + row * scale,
                                  scale, scale, c)
            px += 6 * scale

    def arrowhead(self, x: int, y: int, angle: float, c: tuple,
                  size: int = 11, thick: int = 2) -> None:
        """Стрелка-«V» с остриём в точке (x, y) по направлению ``angle``."""
        for sgn in (1, -1):
            a = angle + sgn * 0.5
            self.line(
                x, y, x - size * math.cos(a), y - size * math.sin(a), c, thick
            )

    def pixel(self, x: int, y: int) -> tuple:
        i = (int(y) * self.w + int(x)) * 3
        return self.buf[i], self.buf[i + 1], self.buf[i + 2]


def encode_png(w: int, h: int, buf: "bytes | bytearray") -> bytes:
    """Кодирование RGB-изображения в PNG (8 бит, без альфы), struct + zlib."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw.extend(buf[y * stride:(y + 1) * stride])
    out = b"\x89PNG\r\n\x1a\n"
    out += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    out += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    out += chunk(b"IEND", b"")
    return out


def decode_png(data: bytes) -> tuple:
    """Служебная расшифровка PNG (для тестов): (w, h, raw).

    ``raw`` — декомпрессированные строки: каждая начинается с байта
    фильтра (0), за которым идут RGB-байты.
    """
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "не PNG"
    pos = 8
    w = h = None
    idat = bytearray()
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        if tag == b"IHDR":
            w, h = struct.unpack(">II", payload[:8])
        elif tag == b"IDAT":
            idat.extend(payload)
        pos += 12 + length
    return w, h, zlib.decompress(bytes(idat))


def pixel_at(data: bytes, x: int, y: int) -> tuple:
    """Цвет пикселя (x, y) в записанном PNG (для тестов)."""
    w, h, raw = decode_png(data)
    i = y * (w * 3 + 1) + 1 + x * 3
    return raw[i], raw[i + 1], raw[i + 2]


def decode_png_pixels(data: bytes) -> tuple:
    """(w, h, пиксель(0,0)) — удобная обёртка над decode_png()."""
    w, h, raw = decode_png(data)
    return w, h, (raw[1], raw[2], raw[3])


BG = (248, 250, 252)
NODE_FILL = (226, 232, 240)
ROOT_FILL = (219, 234, 254)
NODE_EDGE = (71, 85, 105)
NAME_COLOR = (30, 41, 59)
VERSION_COLOR = (100, 116, 139)
TREE_EDGE = (100, 116, 139)
CYCLE_EDGE = (220, 68, 68)
TITLE_COLOR = (15, 23, 42)


def layout(graph) -> tuple:
    """Раскладка: (pos, dims). pos: name -> (x, y); dims — константы рисунка."""
    depth = {graph.root_name: 0}
    for parent, child in graph.tree_edges:
        depth[child] = depth.get(parent, 0) + 1
    levels: dict = {}
    for name in graph.order:
        levels.setdefault(depth[name], []).append(name)

    max_len_name = max(len(n) for n in graph.nodes)
    max_len_ver = max(len(p.version) for p in graph.nodes.values())
    node_w = max(120, min(340, max_len_name * 12 + 28, max_len_ver * 6 + 28))
    node_h = 42
    col_gap = 84
    row_gap = 38
    margin = 26
    top = margin + 40

    max_depth = max(depth.values()) if depth else 0
    max_rows = max(len(v) for v in levels.values()) if levels else 1

    pos = {}
    for d, names in levels.items():
        for i, name in enumerate(names):
            pos[name] = (margin + d * (node_w + col_gap),
                         top + i * (node_h + row_gap))
    canvas_w = margin * 2 + (max_depth + 1) * (node_w + col_gap) - col_gap
    canvas_h = top + max_rows * (node_h + row_gap) + margin - row_gap
    dims = dict(node_w=node_w, node_h=node_h, canvas_w=canvas_w,
                canvas_h=canvas_h)
    return pos, dims


def _draw_node(cv: Canvas, x: int, y: int, dims: dict, name: str,
               version: str, is_root: bool) -> None:
    w, h = dims["node_w"], dims["node_h"]
    fill = ROOT_FILL if is_root else NODE_FILL
    cv.rect(x - 2, y - 2, w + 4, h + 4, NODE_EDGE)
    cv.rect(x, y, w, h, fill)
    cv.text(x + 14, y + 8, name[:48], NAME_COLOR, scale=2)
    cv.text(x + 14, y + 28, version[:56], VERSION_COLOR, scale=1)


def _edge_points(pos: dict, dims: dict, u: str, v: str) -> tuple:
    w, h = dims["node_w"], dims["node_h"]
    x0, y0 = pos[u]
    x1, y1 = pos[v]
    return x0 + w, y0 + h // 2, x1, y1 + h // 2


def render_png(graph) -> tuple:
    """Отрисовать граф в PNG. Возвращает (bytes, width, height)."""
    pos, dims = layout(graph)
    cv = Canvas(dims["canvas_w"], dims["canvas_h"], BG)
    w, h = dims["node_w"], dims["node_h"]
    title = ("DEPENDENCY GRAPH: %s   NODES: %d   CYCLES: %d"
             % (graph.root_name, len(graph.nodes),
                len(graph.describe_cycles())))
    cv.text(26, 12, title, TITLE_COLOR, scale=2)
    ty = 40
    for parent, dep in graph.unresolved[:3]:
        cv.text(26, ty, "UNRESOLVED: %s -> %s" % (parent, dep), CYCLE_EDGE, 1)
        ty += 9

    def draw_edge(u: str, v: str, color: tuple) -> None:
        ax0, ay, bx, by = _edge_points(pos, dims, u, v)
        angle = math.atan2(by - ay, bx - ax0)
        cv.line(ax0, ay, bx - 8, by, color, 2)
        cv.arrowhead(bx - 2, by, angle, color)

    for u, v in graph.tree_edges:
        draw_edge(u, v, TREE_EDGE)
    for u, v in graph.cycle_edges:
        if u in pos and v in pos:
            draw_edge(u, v, CYCLE_EDGE)

    for name, (x, y) in pos.items():
        _draw_node(cv, x, y, dims, name, graph.nodes[name].version,
                   name == graph.root_name)

    png = encode_png(cv.w, cv.h, cv.buf)
    return png, cv.w, cv.h


def _svg_header(graph, cw, ch):
    """Вернуть начальные элементы SVG."""
    cycles = len(graph.describe_cycles())
    title = (
        f'dependency graph: {graph.root_name} '
        f'(nodes: {len(graph.nodes)}, cycles: {cycles})'
    )
    return [
        '<?xml version="1.0" encoding="utf-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{cw}" '
        f'height="{ch}" viewBox="0 0 {cw} {ch}">',
        '<defs>',
        '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#64748b"/></marker>',
        '<marker id="arrc" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#dc4444"/></marker>',
        '</defs>',
        f'<rect x="0" y="0" width="{cw}" height="{ch}" fill="#f8fafc"/>',
        f'<text x="26" y="28" font-family="monospace" '
        f'font-size="15" fill="#0f172a">{title}</text>'
    ]


def _edge_line(pos, dims, u, v, color, dashed=False, marker="arr"):
    """SVG-линия для ребра u -> v."""
    ax, ay, bx, by = _edge_points(pos, dims, u, v)
    dash = ' stroke-dasharray="6 4"' if dashed else ''
    return (
        f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" '
        f'stroke="{color}" stroke-width="2"{dash} '
        f'marker-end="url(#{marker})"/>'
    )


def _node_parts(name, version, x, y, w, h, fill):
    """Вернуть SVG-элементы узла."""
    return [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" '
        f'fill="{fill}" stroke="#475569" stroke-width="2"/>',
        f'<text x="{x + 14}" y="{y + 25}" '
        f'font-family="monospace" font-size="15" '
        f'fill="#1e293b">{_xml_escape(name)}</text>',
        f'<text x="{x + 14}" y="{y + 41}" '
        f'font-family="monospace" font-size="10" '
        f'fill="#64748b">{_xml_escape(version)}</text>',
    ]


def render_svg(graph) -> str:
    """Отрисовать граф в SVG (XML)."""
    pos, dims = layout(graph)
    w, h = dims["node_w"], dims["node_h"]
    cw, ch = dims["canvas_w"], dims["canvas_h"]
    parts = _svg_header(graph, cw, ch)
    for u, v in graph.tree_edges:
        parts.append(_edge_line(pos, dims, u, v, "#64748b"))
    for u, v in graph.cycle_edges:
        if u not in pos or v not in pos:
            continue
        parts.append(
            _edge_line(pos, dims, u, v, "#dc4444", True, "arrc")
        )
    for name, (x, y) in pos.items():
        fill = "#dbeafe" if name == graph.root_name else "#e2e8f0"
        parts.extend(
            _node_parts(name, graph.nodes[name].version, x, y, w, h, fill)
        )
    parts.append('</svg>')
    return "\n".join(parts) + "\n"



def ascii_tree(graph) -> str:
    """Текстовое дерево зависимостей (BFS-дерево) с отметками циклов."""
    children: dict = {}
    for parent, child in graph.tree_edges:
        children.setdefault(parent, []).append(child)
    cycle_set = set(graph.cycle_edges)
    lines = []

    def rec(name: str, prefix: str, is_last: bool, parent: str) -> None:
        pkg = graph.nodes[name]
        connector = "└── " if is_last else "├── "
        note = "  [цикл]" if (parent, name) in cycle_set else ""
        lines.append(prefix + connector + f"{name} {pkg.version}{note}")
        ext = "    " if is_last else "│   "
        ch = children.get(name, [])
        for i, c in enumerate(ch):
            rec(c, prefix + ext, i == len(ch) - 1, name)

    root = graph.root_name
    lines.append(f"{root} {graph.nodes[root].version}")
    ch = children.get(root, [])
    for i, c in enumerate(ch):
        rec(c, "", i == len(ch) - 1, root)
    cycles = graph.describe_cycles()
    if cycles:
        lines.append("")
        for c in cycles:
            lines.append("[цикл] " + " -> ".join(c))
    return "\n".join(lines)
