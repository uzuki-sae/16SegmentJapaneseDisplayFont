import unittest

from seg16 import codec, layout


class TestLayout(unittest.TestCase):
    def test_16_segments_and_9_masked_cells(self):
        self.assertEqual(len(layout.SEGMENT_CELLS), 16)
        cells = set(layout.SEGMENT_CELLS.values())
        masked = {(r, c) for r in range(5) for c in range(5)} - cells
        self.assertEqual(
            masked,
            {(0, 0), (0, 2), (0, 4), (2, 0), (2, 2), (2, 4), (4, 0), (4, 2), (4, 4)},
        )

    def test_positions_match_handwritten_layout(self):
        # 0 1 / 2 3 4 5 6 / 7 8 / 9 A B C D / E F
        expected_rows = [[0, 1], [2, 3, 4, 5, 6], [7, 8], [9, 10, 11, 12, 13], [14, 15]]
        for r, segs in enumerate(expected_rows):
            got = sorted(
                (c, s) for s, (rr, c) in layout.SEGMENT_CELLS.items() if rr == r
            )
            self.assertEqual([s for _, s in got], segs)


class TestSegmentNames(unittest.TestCase):
    def test_names_follow_common_16_segment_labels(self):
        # Wikipedia「Segment display」の 16 セグの図と同じ名前
        expected = {
            0x0: "a1", 0x1: "a2", 0x6: "b", 0xD: "c", 0xE: "d1", 0xF: "d2",
            0x9: "e", 0x2: "f", 0x7: "g1", 0x8: "g2",
            0x3: "h", 0x4: "i", 0x5: "j", 0xA: "k", 0xB: "l", 0xC: "m",
        }
        self.assertEqual({s: layout.SEGMENT_NAMES[s] for s in range(16)}, expected)


class TestCodec(unittest.TestCase):
    def test_segment0_is_msb(self):
        self.assertEqual(codec.segments_to_int({0}), 0x8000)
        self.assertEqual(codec.segments_to_int({15}), 0x0001)

    def test_hex_is_4_digits(self):
        self.assertEqual(codec.to_hex(0x0180), "0180")

    def test_ichi(self):
        # 一 = 中段の横棒 7, 8
        self.assertEqual(codec.to_hex(codec.segments_to_int({7, 8})), "0180")

    def test_roundtrip_all_values(self):
        for v in (0, 1, 0x8000, 0xFFFF, 0x1234, 0xA5C3):
            segs = codec.int_to_segments(v)
            self.assertEqual(codec.segments_to_int(segs), v)
            m = codec.int_to_matrix(v)
            self.assertEqual(codec.matrix_to_int(m), v)
            self.assertEqual(codec.from_hex(codec.to_hex(v)), v)

    def test_matrix_shape_and_mask(self):
        m = codec.int_to_matrix(0xFFFF)
        self.assertEqual(len(m), 5)
        self.assertTrue(all(len(row) == 5 for row in m))
        self.assertEqual(sum(map(sum, m)), 16)
        self.assertEqual(m[0][0], 0)
        self.assertEqual(m[2][2], 0)

    def test_matrix_with_masked_cell_raises(self):
        m = [[0] * 5 for _ in range(5)]
        m[2][2] = 1
        with self.assertRaises(ValueError):
            codec.matrix_to_int(m)


if __name__ == "__main__":
    unittest.main()
