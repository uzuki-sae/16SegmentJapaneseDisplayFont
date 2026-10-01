import os
import tempfile
import unittest

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from seg16 import font

CHARMAP = {"一": "0180", "十": "0990", "〇": "0152"}


class TestBuildFont(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.tmp.name, "test.otf")
        font.build_font(CHARMAP, cls.path)
        cls.font = TTFont(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_is_cff_opentype(self):
        self.assertIn("CFF ", self.font)
        self.assertEqual(self.font.sfntVersion, "OTTO")

    def test_cmap_has_all_chars_and_space(self):
        cmap = self.font.getBestCmap()
        for ch in list(CHARMAP) + [" "]:
            self.assertIn(ord(ch), cmap)

    def test_one_contour_per_lit_segment(self):
        glyphs = self.font.getGlyphSet()
        cmap = self.font.getBestCmap()
        for ch, n in (("一", 2), ("十", 4), ("〇", 4), (" ", 0)):
            pen = RecordingPen()
            glyphs[cmap[ord(ch)]].draw(pen)
            self.assertEqual(sum(op == "closePath" for op, _ in pen.value), n, ch)

    def test_monospaced(self):
        widths = {w for w, _ in self.font["hmtx"].metrics.values()}
        self.assertEqual(len(widths), 1)

    def test_outer_contours_are_counter_clockwise(self):
        # CFF では外側の輪郭を反時計回りにする
        from fontTools.pens.areaPen import AreaPen

        glyphs = self.font.getGlyphSet()
        pen = AreaPen(glyphs)
        glyphs[self.font.getBestCmap()[ord("一")]].draw(pen)
        self.assertGreater(pen.value, 0)


if __name__ == "__main__":
    unittest.main()
