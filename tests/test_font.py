import os
import tempfile
import unittest

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont

from seg16 import font

CHARMAP = {
    "一": "0180", "十": "0990", "〇": "0152", "ア": "C410", "ン": "0520", "无": "C9B1",
    "カ": "05A4", "ハ": "0A24", "ウ": "0985", "゛": "2800", "゜": "A900",
}


class TestVoiced(unittest.TestCase):
    def test_voiced_kana_split_into_base_and_mark(self):
        seq = font.voiced_sequences(CHARMAP)
        self.assertEqual(seq["ガ"], ("カ", "゛"))
        self.assertEqual(seq["が"], ("カ", "゛"))  # ひらがなもカタカナの字形で
        self.assertEqual(seq["パ"], ("ハ", "゜"))
        self.assertEqual(seq["ヴ"], ("ウ", "゛"))
        self.assertNotIn("ギ", seq)  # キ が CHARMAP に無い

    def test_no_voiced_without_marks(self):
        self.assertEqual(font.voiced_sequences({"カ": "05A4"}), {})


class TestAliases(unittest.TestCase):
    def test_digits_and_hiragana_map_to_same_glyphs(self):
        aliases = font.default_aliases(CHARMAP)
        self.assertEqual(aliases["0"], "〇")
        self.assertEqual(aliases["1"], "一")
        self.assertEqual(aliases["１"], "一")  # 全角数字
        self.assertEqual(aliases["あ"], "ア")
        self.assertEqual(aliases["ん"], "ン")
        self.assertEqual(aliases["無"], "无")  # 異体字

    def test_own_zero_glyph_is_used_for_digit_zero(self):
        # 0 に独自の字形があれば、0 と ０ はその字形。1〜9 は漢数字のまま
        aliases = font.default_aliases({**CHARMAP, "0": "A852"})
        self.assertNotIn("0", aliases)
        self.assertEqual(aliases["０"], "0")
        self.assertEqual(aliases["1"], "一")

    def test_fullwidth_latin_and_signs(self):
        aliases = font.default_aliases(
            {"A": "02479B", "a": "79BEF", "+": "0990", "-": "0080", "=": "C180", "ー": "0180"}
        )
        self.assertEqual(aliases["Ａ"], "A")
        self.assertEqual(aliases["ａ"], "a")
        self.assertNotIn("-", aliases)  # - は独自の字形
        self.assertEqual(aliases["－"], "-")  # 全角の記号は半角の記号の字形
        self.assertEqual(aliases["＝"], "=")
        self.assertEqual(aliases["＋"], "+")
        self.assertEqual(aliases["ｰ"], "ー")  # 半角カナの長音符

    def test_no_alias_for_missing_target(self):
        aliases = font.default_aliases(CHARMAP)
        self.assertNotIn("2", aliases)  # 二 は CHARMAP に無い
        self.assertNotIn("き", aliases)


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

    def test_license_and_copyright_in_name_table(self):
        name = self.font["name"]
        self.assertIn("uzuki-sae", name.getDebugName(0))
        self.assertIn("MIT License", name.getDebugName(13))
        self.assertEqual(name.getDebugName(14), "https://opensource.org/license/mit")

    def test_voiced_kana_are_split_by_ccmp(self):
        cmap = self.font.getBestCmap()
        gsub = self.font["GSUB"].table
        features = [f.FeatureTag for f in gsub.FeatureList.FeatureRecord]
        self.assertIn("ccmp", features)
        mapping = {}
        for lookup in gsub.LookupList.Lookup:
            for sub in lookup.SubTable:
                mapping.update(getattr(sub, "mapping", {}))
        self.assertEqual(mapping[cmap[ord("ガ")]], [cmap[ord("カ")], cmap[ord("゛")]])
        self.assertEqual(mapping[cmap[ord("ぱ")]], [cmap[ord("ハ")], cmap[ord("゜")]])

    def test_combining_and_halfwidth_marks_share_glyphs(self):
        cmap = self.font.getBestCmap()
        self.assertEqual(cmap[0x3099], cmap[ord("゛")])
        self.assertEqual(cmap[0xFF9E], cmap[ord("゛")])
        self.assertEqual(cmap[0x309A], cmap[ord("゜")])
        self.assertEqual(cmap[0xFF9F], cmap[ord("゜")])

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
