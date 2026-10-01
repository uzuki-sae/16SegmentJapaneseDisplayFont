"""対照表（文字 → 16進4桁）の組み立て。"""

from .codec import segments_to_int, to_hex


def parse_segments(text):
    """"78EF" のような点灯セグメント番号の列挙をセグメント集合にする。"""
    return {int(c, 16) for c in text}


def apply_overrides(readings, overrides):
    """readings: {文字: 16進4桁}、overrides: {文字: 点灯セグメント番号の列挙}。

    上書き（手書きの読み取りより優先する設定）を適用した新しい対照表を返す。
    """
    result = dict(readings)
    for ch, segs in overrides.items():
        result[ch] = to_hex(segments_to_int(parse_segments(segs)))
    return result


def collisions(table):
    """同じ点灯パターンを持つ文字の組 {16進4桁: [文字, ...]}。"""
    by_code = {}
    for ch, code in table.items():
        by_code.setdefault(code, []).append(ch)
    return {code: chars for code, chars in by_code.items() if len(chars) > 1}
