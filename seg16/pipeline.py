"""手書きシート画像 → 文字ごとの点灯セグメント。"""

from dataclasses import dataclass

from . import recognize, segment

THRESHOLD = 0.6


@dataclass
class Reading:
    char: str
    segments: set
    cell: tuple
    coverages: dict


def read_sheet(image_path, rows, threshold=THRESHOLD):
    ink = segment.hysteresis_ink(segment.load_gray(image_path))
    theta = recognize.orientation(ink)
    glyphs = segment.split_sheet(ink, rows)
    by_band = {}
    for g in glyphs:
        by_band.setdefault(g.band, []).append(g.box)
    refs = {band: recognize.row_reference(boxes) for band, boxes in by_band.items()}
    readings = []
    for g in glyphs:
        cell = recognize.cell_for(g.box, refs[g.band])
        cov = recognize.coverages(ink, cell, theta=theta)
        readings.append(
            Reading(g.char, {s for s, c in cov.items() if c >= threshold}, cell, cov)
        )
    return readings
