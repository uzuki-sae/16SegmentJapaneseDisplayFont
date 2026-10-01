import math
import unittest
import xml.etree.ElementTree as ET

from seg16 import codec, svg

NS = "{http://www.w3.org/2000/svg}"


def _point_segment(p, a, b):
    ax, ay = a
    dx, dy = b[0] - ax, b[1] - ay
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - (ax + t * dx), p[1] - (ay + t * dy))


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _segments_intersect(p1, p2, q1, q2):
    d1, d2 = _cross(q1, q2, p1), _cross(q1, q2, p2)
    d3, d4 = _cross(p1, p2, q1), _cross(p1, p2, q2)
    return (d1 > 0) != (d2 > 0) and (d3 > 0) != (d4 > 0)


def _inside(p, poly):
    # 凸多角形の内側か（頂点は一方向に並んでいる前提）
    signs = [_cross(poly[i], poly[(i + 1) % len(poly)], p) for i in range(len(poly))]
    return all(s > 0 for s in signs) or all(s < 0 for s in signs)


def polygon_distance(pa, pb):
    """2つの凸多角形の距離。重なっていれば 0。"""
    if any(_inside(p, pb) for p in pa) or any(_inside(p, pa) for p in pb):
        return 0.0
    ea = [(pa[i], pa[(i + 1) % len(pa)]) for i in range(len(pa))]
    eb = [(pb[i], pb[(i + 1) % len(pb)]) for i in range(len(pb))]
    if any(_segments_intersect(*e, *f) for e in ea for f in eb):
        return 0.0
    return min(
        min(_point_segment(p, *f) for p in pa for f in eb),
        min(_point_segment(p, *e) for p in pb for e in ea),
    )


class TestSegmentPolygon(unittest.TestCase):
    def test_hexagon_with_pointed_ends(self):
        pts = svg.segment_polygon(0x7, svg.Style())
        self.assertEqual(len(pts), 6)

    def test_polygon_stays_inside_glyph_box(self):
        st = svg.Style()
        for s in range(16):
            for x, y in svg.segment_polygon(s, st):
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x, st.width)
                self.assertLessEqual(y, st.height)

    def test_neighbouring_segments_do_not_touch(self):
        # 0 と 1 の間（上段中央）に隙間がある
        st = svg.Style()
        right_of_0 = max(x for x, _ in svg.segment_polygon(0, st))
        left_of_1 = min(x for x, _ in svg.segment_polygon(1, st))
        self.assertLess(right_of_0, left_of_1)

    def test_no_two_segments_touch(self):
        # 3・4・5 のように中心に集まるセグメントを同時に点灯しても、先端がくっつかない
        for st in (svg.Style(), svg.Style(width=80, height=112, margin=6, thickness=8, gap=2)):
            for a in range(16):
                for b in range(a + 1, 16):
                    with self.subTest(a=a, b=b, style=st):
                        d = polygon_distance(svg.segment_polygon(a, st), svg.segment_polygon(b, st))
                        self.assertGreaterEqual(d, st.gap * 0.99)

    def test_diagonal_is_along_cell_diagonal(self):
        st = svg.Style()
        pts = svg.segment_polygon(0x3, st)
        (ax, ay), (bx, by) = pts[0], pts[3]  # 両端の尖り
        self.assertAlmostEqual(
            math.atan2(by - ay, bx - ax),
            math.atan2(st.height / 2 - st.margin, st.width / 2 - st.margin),
            places=6,
        )


class TestGlyphSvg(unittest.TestCase):
    def test_one_polygon_per_lit_segment(self):
        text = svg.glyph_svg(codec.from_hex("0180"))
        root = ET.fromstring(text)
        self.assertEqual(root.tag, NS + "svg")
        self.assertEqual(len(root.findall(f".//{NS}polygon")), 2)

    def test_ghost_segments_drawn_when_requested(self):
        text = svg.glyph_svg(codec.from_hex("0180"), ghost=True)
        root = ET.fromstring(text)
        self.assertEqual(len(root.findall(f".//{NS}polygon")), 16)


if __name__ == "__main__":
    unittest.main()
