"""対照表（文字 → 16進4桁）の組み立て。"""

from .codec import segments_to_int, to_hex
from .layout import NAME_ORDER, NAME_SEGMENTS, SEGMENT_NAMES


def parse_segments(value):
    """点灯セグメントの指定をセグメント集合にする。

    - 名前のリスト: ["g1", "g2", "d1", "d2"]（a1〜m。layout.SEGMENT_NAMES）
    - セグメント番号の列挙: "78EF"（0〜F）
    b・c・e・f は 16 進の数字と同じ文字なので、名前は必ずリストで書く。
    """
    if isinstance(value, str):
        return {int(c, 16) for c in value}
    unknown = [n for n in value if n not in NAME_SEGMENTS]
    if unknown:
        raise ValueError(f"unknown segment name: {unknown}")
    return {NAME_SEGMENTS[n] for n in value}


def segment_names(segments):
    """セグメント集合を、名前のリスト（a1 a2 b c ... l m の順）にする。"""
    names = {SEGMENT_NAMES[s] for s in segments}
    return [n for n in NAME_ORDER if n in names]


def apply_overrides(readings, overrides):
    """readings: {文字: 16進4桁}、overrides: {文字: 点灯セグメント番号の列挙}。

    上書き（手書きの読み取りより優先する設定）を適用した新しい対照表を返す。
    値が None（JSON の null）の文字は対照表から外す。
    """
    result = dict(readings)
    for ch, segs in overrides.items():
        if segs is None:
            result.pop(ch, None)
        else:
            result[ch] = to_hex(segments_to_int(parse_segments(segs)))
    return result


# ファイル名に使いにくい記号
_UNSAFE = set('\'"/\\:*?<>|.') | {" "}


def svg_filename(ch):
    """文字ごとの SVG ファイル名。記号は U+XXXX 形式にする。

    英字は、大文字と小文字を区別しないファイルシステム（macOS など）でも別のファイルになるよう
    A_upper.svg / a_lower.svg とする。
    """
    if ch.isascii() and ch.isalpha():
        return f"{ch}_{'upper' if ch.isupper() else 'lower'}.svg"
    if ch in _UNSAFE or not ch.isprintable():
        return f"U+{ord(ch):04X}.svg"
    return f"{ch}.svg"


# 同じ字形でよい組み合わせ（重なりとして扱わない）
SAME_LOOKING = [
    {"秒", "゛"},
    {"〇", "零"},
    {"十", "+"},
    {"メ", "X"},
    {"米", "*"},
    {"木", "ホ"},
    {"大", "六"},
    {"/", "ノ"},
    {"<", "ク"},
    {"°", "゜"},
    {":", "時"},
    {"ー", "一", "-"},
]


def collisions(table):
    """同じ点灯パターンを持つ文字の組 {16進4桁: [文字, ...]}。

    重なった文字がすべて SAME_LOOKING のどれか 1 組に含まれる場合は除く。
    """
    by_code = {}
    for ch, code in table.items():
        by_code.setdefault(code, []).append(ch)
    return {
        code: chars
        for code, chars in by_code.items()
        if len(chars) > 1 and not any(set(chars) <= group for group in SAME_LOOKING)
    }
