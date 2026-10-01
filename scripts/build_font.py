"""PART3: 対照表から OpenType フォントを作る。

使い方: python scripts/build_font.py [data/charmap.json] [-o Seg16-Regular.otf]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from seg16 import font  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("charmap", nargs="?", default=str(ROOT / "data" / "charmap.json"))
    ap.add_argument("-o", "--output", default=str(ROOT / "Seg16-Regular.otf"))
    args = ap.parse_args()

    charmap = json.loads(Path(args.charmap).read_text())
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    font.build_font(charmap, str(out))
    print(f"{len(charmap)} 文字 → {out}")


if __name__ == "__main__":
    main()
