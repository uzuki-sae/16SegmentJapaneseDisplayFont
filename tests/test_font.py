import os
import tempfile
import unittest

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from seg16 import font

CHARMAP = {"一": "0180", "十": "0990", "〇": "0152", "ア": "C410", "ン": "0520"}


class TestAliases(unittest.TestCase):
    def test_digits_and_hiragana_map_to_same_glyphs(self):
        aliases = font.default_aliases(CHARMAP)
        self.assertEqual(aliases["0"], "〇")
        self.assertEqual(aliases["1"], "一")
        self.assertEqual(aliases["１"], "一")  # 全角数字
        self.assertEqual(aliases["あ"], "ア")
        self.assertEqual(aliases["ん"], "ン")

    def test_no_alias_for_missing_target(self):
        aliases = font.default_aliases(CHARMAP)
        self.assertNotIn("2", aliases)  # 二 は CHARMAP に無い
        self.assertNotIn("か", aliases)


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

    def test_aliases_share_glyphs(self):
        cmap = self.font.getBestCmap()
        self.assertEqual(cmap[ord("1")], cmap[ord("一")])
        self.assertEqual(cmap[ord("０")], cmap[ord("〇")])
        self.assertEqual(cmap[ord("あ")], cmap[ord("ア")])

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
