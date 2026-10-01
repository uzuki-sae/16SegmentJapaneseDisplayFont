"""切り出した文字画像から、点灯しているセグメントを判定する。

文字枠 (cell) を 2x2 マスとみなし、各セグメントの線分上の点を等間隔にサンプリングする。
インク画素は画の向き（横・縦・＼・／）で4つに分け、セグメントと同じ向きのインクだけを見る。
最寄りの同じ向きのインクまでの距離が許容半径以内の点の割合 (coverage) が
しきい値以上なら点灯とする。向きで分けるので、交差する別の画に引きずられない。
"""

import math

import cv2
import numpy as np

from .layout import SEGMENT_LINES

T_START, T_END, N_SAMPLES = 0.15, 0.85, 15
H, V, BACK, FWD = "H", "V", "\\", "/"


def segment_direction(s):
    (ax, ay), (bx, by) = SEGMENT_LINES[s]
    if ay == by:
        return H
    if ax == bx:
        return V
    return BACK if (bx - ax) * (by - ay) > 0 else FWD


def row_reference(boxes, tall_ratio=0.75):
    """行の中で背の高い文字の上端・下端の中央値を、その行の縦の基準とする。"""
    tallest = max(y1 - y0 for _, y0, _, y1 in boxes)
    tall = [(y0, y1) for _, y0, _, y1 in boxes if y1 - y0 >= tallest * tall_ratio]
    return (int(np.median([t for t, _ in tall])), int(np.median([b for _, b in tall])))


def cell_for(box, reference, min_height_ratio=0.75):
    """文字のインク外接矩形と行の基準から、文字枠 (x0, y0, x1, y1) を決める。

    横は外接矩形をそのまま使う。縦は、背が低い文字（一 など）だけ行の基準を使う。
    """
    x0, y0, x1, y1 = box
    r0, r1 = reference
    if y1 - y0 < (r1 - r0) * min_height_ratio:
        return (x0, r0, x1, r1)
    return (x0, y0, x1, y1)


def orientation(ink, sigma=2.0, window=5.0):
    """構造テンソルで各画素の画の向き（度, 0〜180, 画像座標で y は下向き）を求める。"""
    f = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), sigma)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1)
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), window)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), window)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), window)
    grad = 0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy))
    return (grad + 90.0) % 180.0


def direction_masks(ink, theta, cell):
    """インクを、文字枠の縦横比に合わせた4方向のうち最も近いものに振り分ける。"""
    x0, y0, x1, y1 = cell
    diag = math.degrees(math.atan2(y1 - y0, x1 - x0))
    centers = {H: 0.0, V: 90.0, BACK: diag, FWD: 180.0 - diag}
    diffs = {
        k: np.abs((theta - c + 90.0) % 180.0 - 90.0) for k, c in centers.items()
    }
    best = np.argmin(np.stack(list(diffs.values())), axis=0)
    return {k: ink & (best == i) for i, k in enumerate(diffs)}


def coverages(ink, cell, theta=None, radius_ratio=0.16):
    """セグメントごとの coverage (0〜1) を返す。"""
    if theta is None:
        theta = orientation(ink)
    x0, y0, x1, y1 = cell
    w, h = x1 - x0, y1 - y0
    radius = radius_ratio * min(w, h)
    dists = {
        k: cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
        for k, m in direction_masks(ink, theta, cell).items()
    }
    ts = np.linspace(T_START, T_END, N_SAMPLES)
    result = {}
    for s, ((ax, ay), (bx, by)) in SEGMENT_LINES.items():
        xs = np.clip(np.round(x0 + (ax + (bx - ax) * ts) * w).astype(int), 0, ink.shape[1] - 1)
        ys = np.clip(np.round(y0 + (ay + (by - ay) * ts) * h).astype(int), 0, ink.shape[0] - 1)
        result[s] = float(np.mean(dists[segment_direction(s)][ys, xs] <= radius))
    return result


def read_segments(ink, cell, threshold=0.6, **kwargs):
    return {s for s, c in coverages(ink, cell, **kwargs).items() if c >= threshold}
