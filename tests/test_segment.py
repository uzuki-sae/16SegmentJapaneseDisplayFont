import unittest

from seg16 import segment


class TestPartition(unittest.TestCase):
    def test_wide_internal_gap_stays_in_one_glyph(self):
        # 八: 画どうしの隙間 (56) が、隣の字との隙間 (40) より広い
        comps = [(0, 120), (160, 168), (224, 280), (320, 440)]
        self.assertEqual(
            segment.partition_components(comps, 3, width=120),
            [(0, 120), (160, 280), (320, 440)],
        )

    def test_narrow_glyph_does_not_swallow_neighbour(self):
        # イ: 枠の右半分にだけ描かれた狭い字のすぐ右に ウ がある
        comps = [(0, 90), (155, 200), (160, 175), (245, 310), (295, 370), (420, 540)]
        self.assertEqual(
            segment.partition_components(comps, 4, width=120),
            [(0, 90), (155, 200), (245, 370), (420, 540)],
        )

    def test_narrow_glyph_does_not_take_next_glyphs_first_stroke(self):
        # ク（狭い）のすぐ右に ケ の縦棒があり、その直後に ケ の残りが続く
        comps = [(306, 345), (312, 360), (437, 445), (455, 550), (440, 500), (600, 700)]
        self.assertEqual(
            segment.partition_components(comps, 3, width=118),
            [(306, 360), (437, 550), (600, 700)],
        )

    def test_too_few_components_raises(self):
        with self.assertRaises(ValueError):
            segment.partition_components([(0, 10)], 2, width=120)


if __name__ == "__main__":
    unittest.main()
