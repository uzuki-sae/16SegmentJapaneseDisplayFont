"""手書きシート画像 → 文字ごとの点灯セグメント。"""

from dataclasses import dataclass

import numpy as np

from . import fit, recognize, segment

THRESHOLD = 0.18  # 割り当てられた画の長さがセグメント長のこの割合以上なら点灯
FULL_RATIO = 0.85  # 外接矩形が予想枠のこの割合以上なら、その方向は枠いっぱいに描かれているとみなす


@dataclass
class Reading:
    char: str
    segments: set
    cell: tuple
    coverages: dict
    unexplained: float  # どのセグメントにも当てはまらなかったインクの割合
    pixels: tuple  # この字のインク画素 (ys, xs)

    def doubts(self, threshold=None, margin=0.07, max_unexplained=0.12):
        """確認が必要そうな理由の一覧（空なら問題なさそう）。"""
        threshold = THRESHOLD if threshold is None else threshold
        reasons = []
        near = [s for s, c in self.coverages.items() if abs(c - threshold) < margin]
        if near:
            reasons.append("判定が境界付近: " + ",".join(f"{s:X}" for s in sorted(near)))
        if self.unexplained > max_unexplained:
            reasons.append(f"当てはまらないインク {self.unexplained:.0%}")
        return reasons


def read_sheet(image_path, rows, crop=None, bands=None, threshold=THRESHOLD):
    """crop: (x0, y0, x1, y1) を指定すると、その範囲外のインクを無視する（見出しや罫線を除く）。
    bands: 行ごとの縦の範囲（segment.split_sheet を参照）。
    """
    ink = segment.hysteresis_ink(segment.load_gray(image_path))
    if crop:
        x0, y0, x1, y1 = crop
        keep = np.zeros_like(ink)
        keep[y0:y1, x0:x1] = True
        ink &= keep
    theta = recognize.orientation(ink)
    width = fit.stroke_width(ink)
    glyphs = segment.split_sheet(ink, rows, bands)
    by_band = {}
    for g in glyphs:
        by_band.setdefault(g.band, []).append(g)
    cells = {}
    for row in by_band.values():
        for g, cell in zip(row, recognize.row_cells([g.box for g in row])):
            cells[id(g)] = cell
    readings = []
    for g in glyphs:
        ys, xs = g.pixels
        points = np.stack([xs, ys], axis=1).astype(float)
        prior = cells[id(g)]
        bw, bh = g.box[2] - g.box[0], g.box[3] - g.box[1]
        cell = fit.fit_cell(
            points, theta[ys, xs], prior,
            fix_x=bw >= FULL_RATIO * (prior[2] - prior[0]),
            fix_y=bh >= FULL_RATIO * (prior[3] - prior[1]),
        )
        cov, unexplained = fit.assigned_ratios(points, theta[ys, xs], cell, width)
        readings.append(
            Reading(
                g.char, {s for s, c in cov.items() if c >= threshold}, cell, cov,
                unexplained, g.pixels,
            )
        )
    return readings


def read_sheet_def(sheet, root="."):
    """シート定義（data/*_sheet.json の中身）を読み取る。画像パスは root からの相対パス。"""
    from pathlib import Path

    return read_sheet(
        Path(root) / sheet["image"], sheet["rows"], sheet.get("crop"), sheet.get("bands")
    )
