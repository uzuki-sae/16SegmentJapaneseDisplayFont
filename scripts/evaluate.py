"""手書き画像の読み取り結果を正解データと突き合わせる。

使い方: python scripts/evaluate.py data/kansuji_truth.json [--debug OUT.png]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from seg16 import pipeline  # noqa: E402
from seg16.layout import SEGMENT_LINES  # noqa: E402


def seg_str(segs):
    return "".join(f"{s:X}" for s in sorted(segs))


def parse(text):
    return {int(c, 16) for c in text}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("truth")
    ap.add_argument("--debug", help="判定結果を重ねた画像の出力先")
    args = ap.parse_args()

    truth = json.loads(Path(args.truth).read_text())
    readings = pipeline.read_sheet(ROOT / truth["image"], truth["rows"])

    debug = Image.open(ROOT / truth["image"]).convert("RGB") if args.debug else None
    ok = 0
    for r in readings:
        cov, got = r.coverages, r.segments
        want = parse(truth["segments"][r.char])
        mark = "OK " if got == want else "NG "
        ok += got == want
        detail = ""
        if got != want:
            miss = ",".join(f"{s:X}({cov[s]:.2f})" for s in sorted(want - got))
            extra = ",".join(f"{s:X}({cov[s]:.2f})" for s in sorted(got - want))
            detail = f"  不足:{miss or '-'}  余分:{extra or '-'}"
        print(f"{mark}{r.char} got={seg_str(got):<16} want={seg_str(want):<16}{detail}")
        if debug:
            draw_debug(ImageDraw.Draw(debug), r.cell, got, want)
    print(f"正解 {ok}/{len(readings)}")
    if debug:
        debug.save(args.debug)
    return 0 if ok == len(readings) else 1


def draw_debug(d, cell, got, want):
    x0, y0, x1, y1 = cell
    d.rectangle(cell, outline=(180, 180, 255))
    for s, ((ax, ay), (bx, by)) in SEGMENT_LINES.items():
        if s in got and s in want:
            color = (0, 170, 0)
        elif s in got:
            color = (255, 0, 0)  # 余分
        elif s in want:
            color = (255, 160, 0)  # 不足
        else:
            continue
        w, h = x1 - x0, y1 - y0
        d.line([(x0 + ax * w, y0 + ay * h), (x0 + bx * w, y0 + by * h)], fill=color, width=3)


if __name__ == "__main__":
    sys.exit(main())
