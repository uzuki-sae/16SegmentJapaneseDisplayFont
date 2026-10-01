import math
import unittest
import xml.etree.ElementTree as ET

from seg16 import codec, svg

NS = "{http://www.w3.org/2000/svg}"


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
