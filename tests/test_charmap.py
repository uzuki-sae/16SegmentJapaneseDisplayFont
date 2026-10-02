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
        # 零 と 〇、I と l と 1 なども同じ字形でよい
        self.assertEqual(charmap.collisions({"〇": "C9D3", "零": "C9D3"}), {})
        self.assertEqual(charmap.collisions({"I": "0810", "l": "0810", "1": "0810"}), {})
        # 組の一部だけが重なっても許す
        self.assertEqual(charmap.collisions({"I": "0810", "l": "0810"}), {})


if __name__ == "__main__":
    unittest.main()
