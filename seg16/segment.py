"""手書き画像を行・文字ごとに切り出す。

1. ヒステリシス2値化: 薄いしきい値 (low) でつながる領域のうち、
   濃いしきい値 (high) 未満の画素を含むものだけをインクとする（消し跡を除く）。
2. 行の分割: 横方向の投影で帯を探す。
3. 文字の分割: 帯内の連結成分を x 順に並べ、文字サイズ（帯の高さ）を基準に束ねる。
   1文字の画が離れていても（例: 八）、隙間の大小に頼らず分けられる。
"""

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class Glyph:
    char: str
    box: tuple  # (x0, y0, x1, y1) インク外接矩形。x1, y1 は排他
    band: tuple  # (y0, y1) 行の帯


def load_gray(path):
    return np.asarray(Image.open(path).convert("L"))


def hysteresis_ink(gray, low=225, high=185, min_area=30):
    n, labels, stats, _ = cv2.connectedComponentsWithStats(
        (gray < low).astype(np.uint8), connectivity=8
    )
    dark = np.zeros(n, dtype=bool)
    np.logical_or.at(dark, labels[gray < high], True)
    keep = dark & (stats[:, cv2.CC_STAT_AREA] >= min_area)
    keep[0] = False
    return keep[labels]


def _runs(mask):
    """1次元の bool 配列から True が連続する区間 [(start, end), ...] を返す（end は排他）。"""
    padded = np.concatenate([[False], mask, [False]])
    diff = np.diff(padded.astype(np.int8))
    return list(zip(np.flatnonzero(diff == 1).tolist(), np.flatnonzero(diff == -1).tolist()))


def find_bands(profile, min_ink=1, min_gap=20, min_size=30):
    """投影プロファイルからインクのある帯を探す。min_gap 未満の隙間は同じ帯とみなす。"""
    merged = []
    for s, e in _runs(np.asarray(profile) >= min_ink):
        if merged and s - merged[-1][1] < min_gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return [(s, e) for s, e in merged if e - s >= min_size]


def group_components(ink_band, char_size, join_ratio=0.8, gap_ratio=0.15, max_width_ratio=1.1):
    """帯内の連結成分を x 順に束ね、文字ごとの (x0, x1) を返す。

    次のどちらかなら同じ文字とみなす:
    - 現在の文字の右端との隙間が char_size * gap_ratio 未満
    - 左端が現在の文字の左端 + char_size * join_ratio より左で、
      束ねた幅が char_size * max_width_ratio 以下
    """
    n, _, stats, _ = cv2.connectedComponentsWithStats(ink_band.astype(np.uint8), connectivity=8)
    comps = sorted(
        (stats[i, cv2.CC_STAT_LEFT], stats[i, cv2.CC_STAT_LEFT] + stats[i, cv2.CC_STAT_WIDTH])
        for i in range(1, n)
    )
    groups = []
    for x0, x1 in comps:
        if groups:
            g0, g1 = groups[-1]
            near = x0 - g1 < char_size * gap_ratio
            inside = (
                x0 < g0 + char_size * join_ratio
                and max(g1, x1) - g0 <= char_size * max_width_ratio
            )
            if near or inside:
                groups[-1] = (g0, max(g1, x1))
                continue
        groups.append((x0, x1))
    return groups


def split_sheet(ink, rows):
    """rows: 行ごとの文字列（その行に並ぶ文字を左から順に）。"""
    bands = find_bands(ink.sum(axis=1))
    if len(bands) != len(rows):
        raise ValueError(f"found {len(bands)} rows, expected {len(rows)}: {bands}")
    glyphs = []
    for (y0, y1), chars in zip(bands, rows):
        band = ink[y0:y1]
        spans = group_components(band, char_size=y1 - y0)
        if len(spans) != len(chars):
            raise ValueError(f"row {chars!r}: found {len(spans)} chars: {spans}")
        for ch, (x0, x1) in zip(chars, spans):
            ys = np.flatnonzero(band[:, x0:x1].any(axis=1))
            glyphs.append(Glyph(ch, (x0, y0 + ys[0], x1, y0 + ys[-1] + 1), (y0, y1)))
    return glyphs
