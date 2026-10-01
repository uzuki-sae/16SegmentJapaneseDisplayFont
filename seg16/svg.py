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


CENTER = (0.5, 0.5)


def _is_diagonal(s):
    (ax, ay), (bx, by) = SEGMENT_LINES[s]
    return ax != bx and ay != by


def _direction_from(node, s, st):
    """節点 node から、セグメント s の反対側の端へ向かう単位ベクトル（SVG 座標）。"""
    a, b = SEGMENT_LINES[s]
    other = b if a == node else a
    (x1, y1), (x2, y2) = _grid_point(*node, st), _grid_point(*other, st)
    length = math.hypot(x2 - x1, y2 - y1)
    return ((x2 - x1) / length, (y2 - y1) / length)


def _angle_between(u, v):
    return math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1])))


def _end_shrink(s, node, st):
    """セグメント s の端 node をどれだけ縮めるか。

    先端は六角形で、先端から t/2 進んだ所で太さ t になる。
    - 中心 (最大 8 本が集まる): 隣り合うどの 2 本も gap 以上離れるよう、両方を同じだけ縮める。
      角度 φ の 2 本では、太さが t になる点の二等分線からの距離
      (shrink + t/2)·sin(φ/2) − (t/2)·cos(φ/2) ≥ gap/2 から決まる。
    - 四隅の斜め: 縦横のセグメントは隅の近くまで伸びているとみなし、その帯 (幅 t) から
      gap 以上離れるまで縮める。
    - それ以外の縦横: 一直線に並ぶ隣と gap 以上離れる量 (gap + t/2)。
    """
    t, g = st.thickness, st.gap
    base = g + t / 2
    others = [
        o for o in range(16)
        if o != s and node in SEGMENT_LINES[o]
    ]
    u = _direction_from(node, s, st)
    if node == CENTER:
        need = base
        for o in others:
            phi = _angle_between(u, _direction_from(node, o, st))
            half = phi / 2
            need = max(need, (g / 2 + (t / 2) * math.cos(half)) / math.sin(half) - t / 2)
        return need
    if not _is_diagonal(s):
        return base
    need = base
    for o in others:
        if _is_diagonal(o):
            continue
        phi = _angle_between(u, _direction_from(node, o, st))
        clearance = t / 2 + g
        tip = clearance / math.sin(phi)  # 先端そのもの
        body = (clearance + (t / 2) * math.cos(phi)) / math.sin(phi) - t / 2  # 太さが t になる点
        need = max(need, tip, body)
    return need


def segment_polygon(s, st):
    """セグメント s の六角形の頂点。[先端A, A側上, B側上, 先端B, B側下, A側下]"""
    a, b = SEGMENT_LINES[s]
    (x1, y1), (x2, y2) = _grid_point(*a, st), _grid_point(*b, st)
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length  # 線分方向
    nx, ny = -uy, ux  # 法線
    half = st.thickness / 2
    shrink_a, shrink_b = _end_shrink(s, a, st), _end_shrink(s, b, st)
    tip_a = (x1 + ux * shrink_a, y1 + uy * shrink_a)
    tip_b = (x2 - ux * shrink_b, y2 - uy * shrink_b)
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
