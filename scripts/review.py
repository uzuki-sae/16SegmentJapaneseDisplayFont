"""読み取り結果の確認シート（PNG）を作る。

使い方: python scripts/review.py data/my_sheet.json -o out/review.png
各文字について、左に元の手書き（推定した文字枠を青で表示）、右に読み取ったセグメントを描く。
確認が必要そうな字は赤枠で囲み、理由を書く。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from seg16 import codec, pipeline, svg  # noqa: E402

FONT_PATH = Path.home() / "Library" / "Fonts" / "ipaexg.ttf"
TILE_H = 150
GLYPH = svg.Style(width=80, height=112, margin=6, thickness=8, gap=0.8, diagonal_gap=4.8)


def font(size):
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except OSError:
        return ImageFont.load_default()


def render_segments(segments):
    im = Image.new("RGB", (int(GLYPH.width), int(GLYPH.height)), "white")
    d = ImageDraw.Draw(im)
    for s in range(16):
        color = (20, 20, 20) if s in segments else (232, 232, 232)
        d.polygon(svg.segment_polygon(s, GLYPH), fill=color)
    return im


def tile(src, r, index):
    x0, y0, x1, y1 = r.cell
    pad = int(0.15 * max(x1 - x0, y1 - y0))
    crop = src.crop((x0 - pad, y0 - pad, x1 + pad, y1 + pad)).convert("RGB")
    ImageDraw.Draw(crop).rectangle((pad, pad, pad + x1 - x0, pad + y1 - y0), outline=(90, 140, 255))
    scale = TILE_H / crop.height
    crop = crop.resize((max(1, int(crop.width * scale)), TILE_H))

    doubts = r.doubts()
    w = crop.width + int(GLYPH.width) + 30
    t = Image.new("RGB", (max(w, 240), TILE_H + 62), "white")
    t.paste(crop, (6, 6))
    t.paste(render_segments(r.segments), (crop.width + 18, 6 + (TILE_H - int(GLYPH.height)) // 2))
    d = ImageDraw.Draw(t)
    segs = "".join(f"{s:X}" for s in sorted(r.segments)) or "-"
    hexcode = codec.to_hex(codec.segments_to_int(r.segments))
    d.text((6, TILE_H + 10), f"{index}. {r.char}  {segs}  ({hexcode})", fill="black", font=font(18))
    if doubts:
        d.text((6, TILE_H + 34), " / ".join(doubts), fill=(200, 0, 0), font=font(13))
        d.rectangle((0, 0, t.width - 1, t.height - 1), outline=(220, 0, 0), width=3)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--cols", type=int, default=5)
    args = ap.parse_args()

    sheet = json.loads(Path(args.sheet).read_text())
    src = Image.open(ROOT / sheet["image"])
    readings = pipeline.read_sheet_def(sheet, ROOT)
    tiles = [tile(src, r, i + 1) for i, r in enumerate(readings)]

    tw = max(t.width for t in tiles)
    th = max(t.height for t in tiles)
    rows = (len(tiles) + args.cols - 1) // args.cols
    out = Image.new("RGB", (tw * args.cols + 10 * (args.cols + 1), th * rows + 10 * (rows + 1)), (245, 245, 245))
    for i, t in enumerate(tiles):
        r, c = divmod(i, args.cols)
        out.paste(t, (10 + c * (tw + 10), 10 + r * (th + 10)))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(args.output)

    doubtful = [(i + 1, r) for i, r in enumerate(readings) if r.doubts()]
    print(f"{len(readings)} 文字中 {len(doubtful)} 文字に要確認の印")
    for i, r in doubtful:
        print(f"  {i}. {r.char}: {' / '.join(r.doubts())}")


if __name__ == "__main__":
    main()
