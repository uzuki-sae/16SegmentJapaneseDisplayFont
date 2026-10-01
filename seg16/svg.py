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
    gap: float = 2.5  # 隣り合うセグメントの間の隙間
    on_color: str = "#111111"
    ghost_color: str = "#e6e6e6"


def _grid_point(x, y, st):
    """正規化座標 (0〜1) を SVG 座標に変換する。"""
    return (
        st.margin + x * (st.width - 2 * st.margin),
        st.margin + y * (st.height - 2 * st.margin),
    )


def segment_polygon(s, st):
    """セグメント s の六角形の頂点。[先端A, A側上, B側上, 先端B, B側下, A側下]"""
    (ax, ay), (bx, by) = SEGMENT_LINES[s]
    (x1, y1), (x2, y2) = _grid_point(ax, ay, st), _grid_point(bx, by, st)
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length  # 線分方向
    nx, ny = -uy, ux  # 法線
    half = st.thickness / 2
    diagonal = ax != bx and ay != by
    # 斜めは端で縦横のセグメントと重なりやすいので、多めに縮める
    shrink = st.gap + (st.thickness * 1.2 if diagonal else half)
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
