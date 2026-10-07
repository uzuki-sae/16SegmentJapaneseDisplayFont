import unittest

from seg16 import charmap


class TestCharmap(unittest.TestCase):
    def test_overrides_replace_readings(self):
        readings = {"二": "C003", "一": "0180"}
        self.assertEqual(
            charmap.apply_overrides(readings, {"二": "78EF"}),
            {"二": "0183", "一": "0180"},
        )

    def test_override_for_unread_char_is_added(self):
        self.assertEqual(charmap.apply_overrides({}, {"ミ": "07E"}), {"ミ": "8102"})

    def test_segments_can_be_given_by_name(self):
        self.assertEqual(charmap.parse_segments(["g1", "g2"]), {7, 8})
        self.assertEqual(charmap.parse_segments("78"), {7, 8})
        self.assertEqual(
            charmap.apply_overrides({}, {"一": ["g1", "g2"]}), {"一": "0180"}
        )

    def test_unknown_segment_name_raises(self):
        with self.assertRaises(ValueError):
            charmap.parse_segments(["g3"])

    def test_names_of_segments_in_label_order(self):
        # 表示は a1 a2 b c d1 d2 e f g1 g2 h i j k l m の順
        self.assertEqual(charmap.segment_names({0xF, 7, 8, 0xE}), ["d1", "d2", "g1", "g2"])

    def test_null_override_removes_char(self):
        self.assertEqual(
            charmap.apply_overrides({"木": "08B8", "一": "0180"}, {"木": None}),
            {"一": "0180"},
        )

    def test_svg_filename_distinguishes_letter_case(self):
        # 大文字と小文字を区別しないファイルシステムでも別のファイルになる
        self.assertEqual(charmap.svg_filename("A"), "A_upper.svg")
        self.assertEqual(charmap.svg_filename("a"), "a_lower.svg")

    def test_svg_filename_is_safe_for_symbols(self):
        self.assertEqual(charmap.svg_filename("一"), "一.svg")
        self.assertEqual(charmap.svg_filename('"'), "U+0022.svg")
        self.assertEqual(charmap.svg_filename("'"), "U+0027.svg")
        self.assertEqual(charmap.svg_filename(":"), "U+003A.svg")

    def test_collisions(self):
        self.assertEqual(
            charmap.collisions({"二": "C003", "ニ": "C003", "一": "0180"}),
            {"C003": ["二", "ニ"]},
        )
        self.assertEqual(charmap.collisions({"一": "0180", "二": "C003"}), {})

    def test_same_looking_pair_is_not_a_collision(self):
        # 濁点 ゛ と 秒 は同じ字形でよい組み合わせ
        self.assertEqual(charmap.collisions({"秒": "2800", "゛": "2800"}), {})
        # 零 と 〇 も同じ字形でよい
        self.assertEqual(charmap.collisions({"〇": "C9D3", "零": "C9D3"}), {})

    def test_distinct_letters_must_not_collide(self):
        # I と l、s と 5 は別の字形にしたので、重なれば検出する
        self.assertEqual(charmap.collisions({"I": "0810", "l": "0810"}), {"0810": ["I", "l"]})
        self.assertEqual(charmap.collisions({"s": "A112", "5": "A112"}), {"A112": ["s", "5"]})


if __name__ == "__main__":
    unittest.main()
