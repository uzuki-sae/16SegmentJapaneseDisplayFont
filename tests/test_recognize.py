import unittest

import numpy as np
from PIL import Image, ImageDraw

from seg16 import layout, recognize


def draw_glyph(segments, size=160, margin=40, width=6, gap=0.08):
    """合成画像: 指定セグメントを両端を少し縮めた線で描く。"""
    im = Image.new("L", (size + 2 * margin, size + 2 * margin), 255)
    d = ImageDraw.Draw(im)
    for s in segments:
        (x1, y1), (x2, y2) = layout.SEGMENT_LINES[s]
        ax, ay = x1 + (x2 - x1) * gap, y1 + (y2 - y1) * gap
        bx, by = x2 - (x2 - x1) * gap, y2 - (y2 - y1) * gap
        d.line(
            [(margin + ax * size, margin + ay * size), (margin + bx * size, margin + by * size)],
            fill=60,
            width=width,
        )
    return np.asarray(im) < 200


class TestReadSegments(unittest.TestCase):
    def check(self, segments):
        ink = draw_glyph(segments)
        cell = (40, 40, 200, 200)
        self.assertEqual(recognize.read_segments(ink, cell), set(segments))

    def test_each_single_segment(self):
        for s in range(16):
            with self.subTest(segment=s):
                self.check({s})

    def test_all_segments(self):
        self.check(set(range(16)))

    def test_star_and_box(self):
        self.check({3, 4, 5, 7, 8, 0xA, 0xB, 0xC})
        self.check({0, 1, 2, 6, 9, 0xD, 0xE, 0xF})


    def test_crossing_stroke_does_not_light_diagonal(self):
        # 十 の交点付近に斜めのセグメントを誤検出しない
        self.check({4, 7, 8, 0xB})

    def test_long_diagonal_does_not_light_vertical(self):
        self.check({3, 0xC})
        self.check({5, 0xA})


class TestCells(unittest.TestCase):
    def test_short_glyph_uses_row_reference(self):
        # 一 のように背の低い文字は、行の基準の上下端を使う
        self.assertEqual(recognize.cell_for((10, 95, 170, 105), (20, 180)), (10, 20, 170, 180))

    def test_tall_glyph_uses_own_box(self):
        self.assertEqual(recognize.cell_for((10, 25, 150, 175), (20, 180)), (10, 25, 150, 175))

    def test_row_reference_is_median_of_tall_glyphs(self):
        boxes = [(0, 10, 9, 150), (0, 20, 9, 160), (0, 14, 9, 170), (0, 80, 9, 90)]
        self.assertEqual(recognize.row_reference(boxes), (14, 160))


if __name__ == "__main__":
    unittest.main()
