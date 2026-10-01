"""PART1: 手書きシート画像を読み取り、文字 → 16進4桁 の対照表を作る。

使い方: python scripts/encode.py data/kansuji_truth.json [...] -o data/charmap.json
シート定義 JSON には "image"（画像パス）と "rows"（行ごとの文字列）が必要。
既存の出力ファイルがあれば、同じ文字は上書きし、それ以外は残す。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from seg16 import codec, pipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheets", nargs="+")
    ap.add_argument("-o", "--output", default=str(ROOT / "data" / "charmap.json"))
    args = ap.parse_args()

    out = Path(args.output)
    charmap = json.loads(out.read_text()) if out.exists() else {}
    for sheet_path in args.sheets:
        sheet = json.loads(Path(sheet_path).read_text())
        for r in pipeline.read_sheet(ROOT / sheet["image"], sheet["rows"], sheet.get("crop")):
            charmap[r.char] = codec.to_hex(codec.segments_to_int(r.segments))
            print(r.char, charmap[r.char])
    out.write_text(json.dumps(charmap, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(charmap)} 文字 → {out}")


if __name__ == "__main__":
    main()
