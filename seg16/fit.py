"""文字枠 (cell) の当てはめ。

手書きの字は、外接矩形が 16 セグの枠と一致するとは限らない（枠の一部にだけ描かれた字、
画が枠の端まで届いていない字など）。そこで枠の位置と大きさを探索し、
インクの各画素が「同じ向きのセグメントの線分」の近くにあるほど高い点を与える。

縦横の画だけの字は半マスずらしても同じように当てはまるので、
予想位置（prior）や標準サイズから離れるほど減点して決める。
"""

import itertools
import math

import numpy as np

from .layout import SEGMENT_LINES

SCALES = (0.85, 0.92, 1.0, 1.08, 1.15)
_LINES = np.array([SEGMENT_LINES[s] for s in range(16)], dtype=np.float64)  # (16, 2, 2)


def segment_match(px, py, pa, x0, y0, w, h, sigma_ratio=0.08, max_angle=30.0):
    """各画素とセグメントの当てはまり (0〜1)。px, py, pa: (N,), x0, y0: (M,) → (M, 16, N)"""
    ax = x0[:, None, None] + _LINES[None, :, 0, 0, None] * w  # (M, 16, 1)
    ay = y0[:, None, None] + _LINES[None, :, 0, 1, None] * h
    bx = x0[:, None, None] + _LINES[None, :, 1, 0, None] * w
    by = y0[:, None, None] + _LINES[None, :, 1, 1, None] * h
    dx, dy = bx - ax, by - ay
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    dist = np.hypot(px - (ax + t * dx), py - (ay + t * dy))  # (M, 16, N)
    seg_angle = np.degrees(np.arctan2(dy, dx)) % 180.0  # (M, 16, 1)
    diff = np.abs((pa - seg_angle + 90.0) % 180.0 - 90.0)
    sigma = sigma_ratio * min(w, h)
    return np.exp(-((dist / sigma) ** 2)) * (diff < max_angle)


def _match(px, py, pa, x0, y0, w, h):
    """各画素の、最も合うセグメントとの当てはまり。→ (M, N)"""
    return segment_match(px, py, pa, x0, y0, w, h).max(axis=1)


def stroke_width(ink):
    """線幅の推定値（画素）。幅 W の帯の距離変換値は 0〜W/2 に一様に分布するので、中央値の 4 倍。"""
    import cv2

    dist = cv2.distanceTransform(ink.astype(np.uint8), cv2.DIST_L2, 5)
    return 4.0 * float(np.median(dist[ink]))


def assigned_ratios(points, angles, cell, width, sigma_ratio=0.14, min_match=0.3):
    """インク画素を最も合うセグメントに割り当てる。

    戻り値: ({セグメント: 割り当てられた画の長さ ÷ セグメントの長さ}, どのセグメントにも
    当てはまらなかった画素の割合)。短い画でも、その位置と向きに描かれていれば値が出る。
    """
    x0, y0, x1, y1 = cell
    w, h = x1 - x0, y1 - y0
    m = segment_match(
        points[:, 0], points[:, 1], angles,
        np.array([x0], float), np.array([y0], float), w, h, sigma_ratio=sigma_ratio,
    )[0]  # (16, N)
    best = m.argmax(axis=0)
    matched = m.max(axis=0) >= min_match
    counts = np.bincount(best[matched], minlength=16)
    lengths = np.hypot((_LINES[:, 1, 0] - _LINES[:, 0, 0]) * w, (_LINES[:, 1, 1] - _LINES[:, 0, 1]) * h)
    ratios = {s: float(counts[s] / width / lengths[s]) for s in range(16)}
    return ratios, float(1.0 - matched.mean())


def _candidates(lo, hi, size, fixed_start, fixed, tolerance, step):
    """枠の始点の候補。fixed なら予想位置の近くだけ、そうでなければインクを含む範囲すべて。"""
    if fixed:
        return np.arange(fixed_start - 2 * step, fixed_start + 2 * step + 1, step, dtype=float)
    return np.arange(hi - tolerance * size - size, lo + tolerance * size + 1, step, dtype=float)


def fit_cell(
    points, angles, prior, fix_x=False, fix_y=False,
    step=3, max_points=400, tolerance=0.1, weight=0.5,
):
    """points: (N, 2) の (x, y)、angles: (N,) 画の向き（度）、prior: 予想される枠 (x0, y0, x1, y1)。

    fix_x / fix_y: その方向は外接矩形が信頼できる（枠いっぱいに描かれている）ので動かさない。
    """
    if len(points) > max_points:
        idx = np.linspace(0, len(points) - 1, max_points).astype(int)
        points, angles = points[idx], angles[idx]
    px, py, pa = points[:, 0], points[:, 1], angles
    bx0, by0, bx1, by1 = px.min(), py.min(), px.max(), py.max()
    pw, ph = prior[2] - prior[0], prior[3] - prior[1]
    pcx, pcy = (prior[0] + prior[2]) / 2, (prior[1] + prior[3]) / 2
    best, best_cell = -math.inf, tuple(prior)
    for sw, sh in itertools.product((1.0,) if fix_x else SCALES, (1.0,) if fix_y else SCALES):
        w, h = pw * sw, ph * sh
        xs = _candidates(bx0, bx1, w, prior[0], fix_x, tolerance, step)
        ys = _candidates(by0, by1, h, prior[1], fix_y, tolerance, step)
        if len(xs) == 0 or len(ys) == 0:
            continue
        gx, gy = (g.ravel() for g in np.meshgrid(xs, ys))
        fit = _match(px, py, pa, gx, gy, w, h).mean(axis=1)
        penalty = weight * (
            ((gx + w / 2 - pcx) / pw) ** 2
            + ((gy + h / 2 - pcy) / ph) ** 2
            + (sw - 1) ** 2
            + (sh - 1) ** 2
        )
        total = fit - penalty
        i = int(np.argmax(total))
        if total[i] > best:
            best = float(total[i])
            best_cell = (gx[i], gy[i], gx[i] + w, gy[i] + h)
    return tuple(int(round(v)) for v in best_cell)
