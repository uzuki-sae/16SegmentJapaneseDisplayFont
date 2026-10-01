import unittest

import numpy as np

from seg16 import fit, recognize
from tests.test_recognize import draw_glyph

TRUE_CELL = (40, 40, 200, 200)


def fitted(segments, prior):
    ink = draw_glyph(segments)
    theta = recognize.orientation(ink)
    ys, xs = np.nonzero(ink)
    return fit.fit_cell(np.stack([xs, ys], axis=1).astype(float), theta[ys, xs], prior)


class TestFitCell(unittest.TestCase):
    def assertCellClose(self, cell, expected, tol=8):
        for a, b in zip(cell, expected):
            self.assertLessEqual(abs(a - b), tol, f"{cell} != {expected}")

    def test_ku_shape_is_anchored_by_diagonals(self):
        # ク = 5, C（「く」の頂点が枠の中心）。インクは枠の右半分だけ
        # 予想枠: 標準サイズだが、インクの中心に合わせたため右にずれている
        ys, xs = np.nonzero(draw_glyph({5, 0xC}))
        cx = (xs.min() + xs.max()) / 2
        prior = (cx - 80, 40, cx + 80, 200)
        self.assertCellClose(fitted({5, 0xC}, prior), TRUE_CELL)

    def test_half_width_box_follows_prior(self):
        # 7,9,B,E（左下の小さな四角）は、予想位置に近い置き方を選ぶ
        self.assertCellClose(fitted({7, 9, 0xB, 0xE}, (45, 40, 205, 200)), TRUE_CELL)

    def test_full_glyph_keeps_true_cell(self):
        segs = {0, 1, 2, 6, 7, 8, 9, 0xD, 0xE, 0xF}
        self.assertCellClose(fitted(segs, (30, 30, 210, 210)), TRUE_CELL)


if __name__ == "__main__":
    unittest.main()
