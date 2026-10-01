"""PART1: 手書きシート画像を読み取り、文字 → 16進4桁 の対照表を作る。

使い方: python scripts/encode.py [data/*_sheet.json ...] [-o data/charmap.json]
シート定義 JSON には "image"（画像パス）と "rows"（行ごとの文字列。"_" は空きマス）、
必要なら "crop"（読み取り範囲）を書く。シートを省略すると data/*_sheet.json をすべて読む。

読み取り結果に data/overrides.json（{文字: 点灯セグメント番号の列挙}）の上書きを適用し、
同じ点灯パターンの文字があれば一覧を出して終了コード 1 を返す。
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from seg16 import charmap, codec, pipeline  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheets", nargs="*")
    ap.add_argument("-o", "--output", default=str(ROOT / "data" / "charmap.json"))
    ap.add_argument("--overrides", default=str(ROOT / "data" / "overrides.json"))
    args = ap.parse_args()

    sheets = args.sheets or sorted(str(p) for p in (ROOT / "data").glob("*_sheet.json"))
    if not sheets:
        # シートが無いまま進むと、上書き表だけの対照表で data/charmap.json を消してしまう
        print("シート定義 (data/*_sheet.json) がありません。", file=sys.stderr)
        return 2
    readings = {}
    for sheet_path in sheets:
        sheet = json.loads(Path(sheet_path).read_text())
        for r in pipeline.read_sheet_def(sheet, ROOT):
            readings[r.char] = codec.to_hex(codec.segments_to_int(r.segments))
        print(f"{sheet_path}: 読み取り済み")

    overrides_path = Path(args.overrides)
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}
    table = charmap.apply_overrides(readings, overrides)
    for ch in overrides:
        before = readings.get(ch, "----")
        after = table.get(ch, "削除")
        if before != after:
            print(f"  上書き {ch}: {before} → {after}")

    out = Path(args.output)
    out.write_text(json.dumps(table, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(table)} 文字 → {out}")

    dup = charmap.collisions(table)
    for code, chars in dup.items():
        print(f"重なり {code}: {' '.join(chars)}")
    return 1 if dup else 0


if __name__ == "__main__":
    sys.exit(main())
