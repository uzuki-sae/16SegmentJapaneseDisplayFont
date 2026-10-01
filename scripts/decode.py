"""PART2: 対照表から文字ごとの SVG と一覧ページを生成する。

使い方: python scripts/decode.py [data/charmap.json] [-o svg]
出力: svg/<文字>.svg と svg/index.html（消灯セグメントを薄く表示した一覧）
"""

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from seg16 import charmap as charmap_mod  # noqa: E402
from seg16 import codec, svg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("charmap", nargs="?", default=str(ROOT / "data" / "charmap.json"))
    ap.add_argument("-o", "--outdir", default=str(ROOT / "svg"))
    args = ap.parse_args()

    charmap = json.loads(Path(args.charmap).read_text())
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cards = []
    for ch, hexcode in charmap.items():
        value = codec.from_hex(hexcode)
        (outdir / charmap_mod.svg_filename(ch)).write_text(svg.glyph_svg(value))
        cards.append(
            f'<figure>{svg.glyph_svg(value, ghost=True)}'
            f"<figcaption>{html.escape(ch)} {hexcode}</figcaption></figure>"
        )
    (outdir / "index.html").write_text(
        "<!doctype html><meta charset='utf-8'><title>16seg</title>"
        "<style>body{display:flex;flex-wrap:wrap;gap:12px;font-family:sans-serif}"
        "figure{margin:0;text-align:center}figure svg{width:60px;height:auto}</style>\n" + "\n".join(cards) + "\n"
    )
    print(f"{len(charmap)} 文字 → {outdir}")


if __name__ == "__main__":
    main()
