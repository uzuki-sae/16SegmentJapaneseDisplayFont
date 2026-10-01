"""セグメント集合・5x5 行列・16bit 整数・16進文字列の相互変換。

ビット順: セグメント 0 が最上位ビット (0x8000)、セグメント F が最下位ビット (0x0001)。
"""

from .layout import CELL_SEGMENTS, SEGMENT_CELLS


def segments_to_int(segments):
    value = 0
    for s in segments:
        if not 0 <= s <= 15:
            raise ValueError(f"segment out of range: {s}")
        value |= 1 << (15 - s)
    return value


def int_to_segments(value):
    if not 0 <= value <= 0xFFFF:
        raise ValueError(f"value out of range: {value}")
    return {s for s in range(16) if value & (1 << (15 - s))}


def int_to_matrix(value):
    m = [[0] * 5 for _ in range(5)]
    for s in int_to_segments(value):
        r, c = SEGMENT_CELLS[s]
        m[r][c] = 1
    return m


def matrix_to_int(matrix):
    segments = set()
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            if not v:
                continue
            if (r, c) not in CELL_SEGMENTS:
                raise ValueError(f"masked cell is set: {(r, c)}")
            segments.add(CELL_SEGMENTS[(r, c)])
    return segments_to_int(segments)


def to_hex(value):
    return f"{value:04X}"


def from_hex(text):
    return int(text, 16)
