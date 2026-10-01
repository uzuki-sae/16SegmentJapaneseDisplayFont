"""点灯パターン（16bit 整数）から SVG を描画する。

各セグメントは両端を尖らせた六角形（7セグ表示器のような形）にする。
"""

import math
from dataclasses import dataclass

from .codec import int_to_segments
from .layout import SEGMENT_LINES


@dataclass
class Style:
    width: float = 100.0
    height: float = 140.0
    margin: float = 8.0  # 外枠から格子線までの余白
    thickness: float = 10.0
    gap: float = 1.0  # 隣り合う縦横セグメントの間の隙間
    diagonal_gap: float = 6.0  # 斜めセグメントと周りのセグメントの間の隙間
    on_color: str = "#111111"
    ghost_color: str = "#e6e6e6"


def _grid_point(x, y, st):
    """正規化座標 (0〜1) を SVG 座標に変換する。"""
    return (
        st.margin + x * (st.width - 2 * st.margin),
        st.margin + y * (st.height - 2 * st.margin),
    )


def _is_diagonal(s):
    (ax, ay), (bx, by) = SEGMENT_LINES[s]
    return ax != bx and ay != by


def _clip(poly, nx, ny, c):
    """凸多角形 poly を半平面 nx*x + ny*y <= c で切り取る（Sutherland–Hodgman）。"""
    out = []
    for p, q in zip(poly, poly[1:] + poly[:1]):
        fp, fq = nx * p[0] + ny * p[1] - c, nx * q[0] + ny * q[1] - c
        if fp <= 0:
            out.append(p)
        if (fp < 0 < fq) or (fq < 0 < fp):
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def _diagonal_polygon(s, st):
    """斜めのセグメント: 軸に沿った幅 t の帯と、そのマスの内側の長方形の重なり。

    長方形は、マスを囲む縦横のセグメントの太さ (t/2) と隙間 (diagonal_gap) の分だけ内側に寄せたもの。
    先端は隣の縦横と平行（水平・垂直）に切れるので、隣との隙間がどこでも diagonal_gap になる。
    """
    (ax, ay), (bx, by) = SEGMENT_LINES[s]
    (x1, y1), (x2, y2) = _grid_point(ax, ay, st), _grid_point(bx, by, st)
    inset = st.thickness / 2 + st.diagonal_gap
    left, right = min(x1, x2) + inset, max(x1, x2) - inset
    top, bottom = min(y1, y2) + inset, max(y1, y2) - inset
    poly = [(left, top), (right, top), (right, bottom), (left, bottom)]
    length = math.hypot(x2 - x1, y2 - y1)
    nx, ny = -(y2 - y1) / length, (x2 - x1) / length  # 軸の法線
    offset = nx * x1 + ny * y1
    half = st.thickness / 2
    poly = _clip(poly, nx, ny, offset + half)
    poly = _clip(poly, -nx, -ny, -(offset - half))
    return poly


def segment_polygon(s, st):
    """セグメント s の多角形の頂点。

    縦横: 両端を尖らせた六角形 [先端A, A側上, B側上, 先端B, B側下, A側下]。
    斜め: 先端を水平・垂直に切った多角形（_diagonal_polygon）。
    """
    if _is_diagonal(s):
        return _diagonal_polygon(s, st)
    a, b = SEGMENT_LINES[s]
    (x1, y1), (x2, y2) = _grid_point(*a, st), _grid_point(*b, st)
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length  # 線分方向
    nx, ny = -uy, ux  # 法線
    half = st.thickness / 2
    shrink = st.gap + half  # 一直線に並ぶ隣・直交する縦横と gap 以上離れる
    tip_a = (x1 + ux * shrink, y1 + uy * shrink)
    tip_b = (x2 - ux * shrink, y2 - uy * shrink)
    a_in = (tip_a[0] + ux * half, tip_a[1] + uy * half)
    b_in = (tip_b[0] - ux * half, tip_b[1] - uy * half)
    return [
        tip_a,
        (a_in[0] + nx * half, a_in[1] + ny * half),
        (b_in[0] + nx * half, b_in[1] + ny * half),
        tip_b,
        (b_in[0] - nx * half, b_in[1] - ny * half),
        (a_in[0] - nx * half, a_in[1] - ny * half),
    ]


def _polygon(s, st, color):
    pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in segment_polygon(s, st))
    return f'  <polygon data-seg="{s:X}" points="{pts}" fill="{color}"/>'


def glyph_svg(value, st=None, ghost=False):
    """ghost=True なら消灯セグメントも薄く描く（表示器風のプレビュー用）。"""
    st = st or Style()
    lit = int_to_segments(value)
    body = []
    for s in range(16):
        if s in lit:
            body.append(_polygon(s, st, st.on_color))
        elif ghost:
            body.append(_polygon(s, st, st.ghost_color))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {st.width:g} {st.height:g}" '
        f'width="{st.width:g}" height="{st.height:g}">\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )
