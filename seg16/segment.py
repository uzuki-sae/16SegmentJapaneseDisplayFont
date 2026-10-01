"""手書き画像を行・文字ごとに切り出す。

1. ヒステリシス2値化: 薄いしきい値 (low) でつながる領域のうち、
   濃いしきい値 (high) 未満の画素を含むものだけをインクとする（消し跡を除く）。
2. 行の分割: 横方向の投影のインク区間を、大きい隙間から順に（行数-1）か所で切る。
3. 文字の分割: 帯内の連結成分を中心の x 順に並べ、行の文字数ちょうどに分ける。
   各文字の幅が標準幅に近く、切れ目の隙間が広い分け方を動的計画法で選ぶ。
   画どうしが離れた字（八）や、枠の片側だけに描かれた狭い字（イ）も分けられる。
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
    pixels: tuple = None  # この字に割り当てたインク画素 (ys, xs)
    row: int = 0  # 行番号
    col: int = 0  # 行の中での位置（空きマス "_" も数える）


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


def split_by_largest_gaps(profile, count, min_ink=1):
    """プロファイルのインク区間を、大きい隙間から順に count-1 か所で切って count 個にまとめる。"""
    runs = _runs(np.asarray(profile) >= min_ink)
    if len(runs) < count:
        raise ValueError(f"ink runs ({len(runs)}) fewer than expected ({count})")
    cuts = sorted(
        sorted(range(len(runs) - 1), key=lambda i: runs[i + 1][0] - runs[i][1], reverse=True)[
            : count - 1
        ]
    )
    spans, start = [], 0
    for i in cuts:
        spans.append((runs[start][0], runs[i][1]))
        start = i + 1
    spans.append((runs[start][0], runs[-1][1]))
    return spans


def _width_cost(w, width):
    """幅のコスト。広すぎる字は強く、狭すぎる字は弱く減点する（狭い字は普通にある: ク・ノ・イ）。"""
    over = max(0.0, w - 1.1 * width)
    under = max(0.0, 0.9 * width - w)
    return 4.0 * over**2 + 0.1 * under**2


def _partition(intervals, count, width, min_gap_ratio=0.6):
    """x 区間の列（中心の x 順）を、連続する count 個のグループに分ける。

    コスト = Σ 幅のコスト + Σ max(0, width*min_gap_ratio - 切れ目の隙間)^2
    を最小にする分け方を動的計画法で求め、グループごとのインデックスの範囲を返す。
    """
    n = len(intervals)
    if n < count:
        raise ValueError(f"components ({n}) fewer than expected chars ({count})")
    min_gap = width * min_gap_ratio
    span = [[None] * (n + 1) for _ in range(n)]  # span[i][j]: intervals[i:j] の (x0, x1)
    for i in range(n):
        x0, x1 = intervals[i]
        for j in range(i + 1, n + 1):
            x0, x1 = min(x0, intervals[j - 1][0]), max(x1, intervals[j - 1][1])
            span[i][j] = (x0, x1)
    inf = float("inf")
    # best[k][j]: intervals[:j] を k グループに分けたときの (コスト, 直前の切れ目)
    best = [[(inf, -1)] * (n + 1) for _ in range(count + 1)]
    best[0][0] = (0.0, -1)
    for k in range(1, count + 1):
        for j in range(k, n + 1):
            for i in range(k - 1, j):
                prev = best[k - 1][i][0]
                if prev == inf:
                    continue
                x0, x1 = span[i][j]
                cost = prev + _width_cost(x1 - x0, width)
                if i > 0:
                    gap = x0 - span[best[k - 1][i][1] if k > 1 else 0][i][1]
                    cost += max(0.0, min_gap - gap) ** 2
                if cost < best[k][j][0]:
                    best[k][j] = (cost, i)
    bounds, j = [], n
    for k in range(count, 0, -1):
        i = best[k][j][1]
        bounds.append((i, j))
        j = i
    return bounds[::-1]


def partition_components(intervals, count, width):
    """x 区間を count 文字に分け、文字ごとの (x0, x1) を返す。"""
    order = sorted(intervals, key=lambda iv: iv[0] + iv[1])
    result = []
    for i, j in _partition(order, count, width):
        result.append((min(x0 for x0, _ in order[i:j]), max(x1 for _, x1 in order[i:j])))
    return result


EMPTY = "_"  # 表の空きマス


def split_sheet(ink, rows, bands=None):
    """rows: 行ごとの文字列（その行に並ぶ文字を左から順に。"_" は空きマス）。

    bands: 行ごとの縦の範囲 [(y0, y1), ...]。省略すると自動で分ける。
    隣の行と画を共有する字（縦に続けて描いた 上・下）は範囲を重ねて指定する。
    """
    if bands is None:
        bands = split_by_largest_gaps(ink.sum(axis=1), len(rows))
    elif len(bands) != len(rows):
        raise ValueError(f"bands ({len(bands)}) と rows ({len(rows)}) の数が違う")
    bands = [tuple(b) for b in bands]
    # 文字の標準幅の目安: 行の高さの中央値の 0.8 倍
    width = 0.8 * float(np.median([y1 - y0 for y0, y1 in bands]))
    glyphs = []
    for row_no, ((y0, y1), row) in enumerate(zip(bands, rows)):
        chars = [(c, ch) for c, ch in enumerate(row) if ch != EMPTY]
        n, labels, st, _ = cv2.connectedComponentsWithStats(
            ink[y0:y1].astype(np.uint8), connectivity=8
        )
        boxes = sorted(
            (
                (st[i, 0], y0 + st[i, 1], st[i, 0] + st[i, 2], y0 + st[i, 1] + st[i, 3], i)
                for i in range(1, n)
            ),
            key=lambda b: b[0] + b[2],
        )
        groups = _partition([(b[0], b[2]) for b in boxes], len(chars), width)
        for (col, ch), (i, j) in zip(chars, groups):
            part = boxes[i:j]
            box = (
                min(b[0] for b in part),
                min(b[1] for b in part),
                max(b[2] for b in part),
                max(b[3] for b in part),
            )
            ys, xs = np.nonzero(np.isin(labels, [b[4] for b in part]))
            glyphs.append(
                Glyph(ch, tuple(int(v) for v in box), (y0, y1), (ys + y0, xs), row_no, col)
            )
    return glyphs
