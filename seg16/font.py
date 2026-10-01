"""PART3: 対照表から OpenType (CFF) フォントを作る。

輪郭は SVG と同じセグメント形状 (svg.segment_polygon) から作るので、SVG とフォントの見た目は一致する。
SVG 座標（y が下向き）を、フォント座標（y が上向き、ベースライン y=0）に変換する。
"""

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen

from .codec import from_hex, int_to_segments
from .svg import Style, segment_polygon

UNITS_PER_EM = 1000
SCALE = 6.5  # SVG 1 単位 → フォント単位。Style の 100x140 が 650x910 になる
DESCENT = 120  # 字の下端をベースラインからどれだけ下げるか
FAMILY = "Seg16"
COPYRIGHT = "Copyright (c) 2026 uzuki-sae"
LICENSE = "This Font Software is licensed under the MIT License."
LICENSE_URL = "https://opensource.org/license/mit"
KANSUJI = "〇一二三四五六七八九"
HIRAGANA_OFFSET = 0x60  # ひらがな = カタカナ - 0x60（ぁ U+3041 〜 ゖ U+3096）


def default_aliases(charmap):
    """別の文字コードから同じ字形を出すための対応 {別名の文字: 対照表の文字}。

    - アラビア数字 0〜9 と全角数字 ０〜９ → 漢数字 〇〜九
    - ひらがな → 対応するカタカナ
    対照表に無い字への対応や、対照表に既にある字の上書きは作らない。
    """
    aliases = {}
    for i, kan in enumerate(KANSUJI):
        aliases[str(i)] = kan
        aliases[chr(ord("０") + i)] = kan
    for kata in charmap:
        if "\u30a1" <= kata <= "\u30f6":
            aliases[chr(ord(kata) - HIRAGANA_OFFSET)] = kata
    return {a: t for a, t in aliases.items() if t in charmap and a not in charmap}


def _signed_area(points):
    return sum(
        x0 * y1 - x1 * y0
        for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1])
    ) / 2


def glyph_contours(value, st):
    """点灯セグメントごとの輪郭（フォント座標、反時計回り）。"""
    contours = []
    for s in sorted(int_to_segments(value)):
        pts = [
            (round(x * SCALE), round((st.height - y) * SCALE) - DESCENT)
            for x, y in segment_polygon(s, st)
        ]
        if _signed_area(pts) < 0:
            pts.reverse()
        contours.append(pts)
    return contours


def _charstring(contours, width):
    pen = T2CharStringPen(width, None)
    for pts in contours:
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()
    return pen.getCharString()


def glyph_name(ch):
    return f"uni{ord(ch):04X}" if ord(ch) <= 0xFFFF else f"u{ord(ch):05X}"


def build_font(charmap, path, st=None, family=FAMILY, version="0.1", aliases=None):
    """charmap: {文字: 16進4桁}。path に .otf を書き出す。

    aliases: {別名の文字: 対照表の文字}。省略すると default_aliases を使う。
    """
    aliases = default_aliases(charmap) if aliases is None else aliases
    st = st or Style()
    width = round(st.width * SCALE)
    ascent = round(st.height * SCALE) - DESCENT

    names = {ch: glyph_name(ch) for ch in charmap}
    order = [".notdef", "space"] + [names[ch] for ch in charmap]
    charstrings = {
        ".notdef": _charstring(glyph_contours(0xFFFF, st), width),
        "space": _charstring([], width),
    }
    for ch, hexcode in charmap.items():
        charstrings[names[ch]] = _charstring(glyph_contours(from_hex(hexcode), st), width)

    fb = FontBuilder(UNITS_PER_EM, isTTF=False)
    fb.setupGlyphOrder(order)
    cmap = {ord(" "): "space", **{ord(ch): names[ch] for ch in charmap}}
    cmap.update({ord(a): names[t] for a, t in aliases.items()})
    fb.setupCharacterMap(cmap)
    fb.setupCFF(
        f"{family}-Regular", {"FullName": f"{family} Regular"}, charstrings, {}
    )
    fb.setupHorizontalMetrics({g: (width, 0) for g in order})
    fb.setupHorizontalHeader(ascent=ascent, descent=-DESCENT)
    fb.setupNameTable(
        {
            "copyright": COPYRIGHT,
            "familyName": family,
            "styleName": "Regular",
            "uniqueFontIdentifier": f"{family}-Regular-{version}",
            "fullName": f"{family} Regular",
            "psName": f"{family}-Regular",
            "version": f"Version {version}",
            "licenseDescription": LICENSE,
            "licenseInfoURL": LICENSE_URL,
        }
    )
    fb.setupOS2(
        sTypoAscender=ascent,
        sTypoDescender=-DESCENT,
        sTypoLineGap=0,
        usWinAscent=ascent,
        usWinDescent=DESCENT,
        xAvgCharWidth=width,
        fsType=0,
    )
    fb.setupPost(isFixedPitch=1)
    fb.save(path)
