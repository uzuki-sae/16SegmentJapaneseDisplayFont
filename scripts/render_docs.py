"""README 用の画像を作る。

使い方: python scripts/render_docs.py [data/charmap.json] [-o docs]
出力:
  docs/segments.png  セグメント番号の配置図
  docs/charmap.png   対照リスト（字形・文字・16進コード）
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from seg16 import codec, svg  # noqa: E402

FONT_PATH = Path.home() / "Library" / "Fonts" / "ipaexg.ttf"
ON, OFF, INK, SUB = (20, 20, 20), (228, 228, 228), (30, 30, 30), (120, 120, 120)
DIGITS = "0123456789"
KANSUJI = "〇一二三四五六七八九十百千万円零"
MARKS = "゛゜、。ー+−-=_/\\<>*%°():."
# 字そのものでは読みにくいものの表示名
LABELS = {
    "゛": "濁点", "゜": "半濁点", "、": "読点", "。": "句点", "ー": "長音符",
    "−": "マイナス", "-": "ハイフン", "_": "下線", ".": "ピリオド", ":": "コロン", "°": "度",
}
# 他の資料の字形に基づく字の出典
WIKIMEDIA_NOTE = (
    "ソ・ヘ・ム の字形は、Wikimedia Commons「16SISD-Katakana.gif」"
    "（作者 Arumaddilo、CC BY-SA 4.0）に基づきます"
)
# 本来の字形とは別の形で表している字・出典のある字（対照リストに ※ を付けて注記する）
NOTES = {
    "ク": "ク は、ひらがなの「く」の形で表しています",
    "キ": "キ は、「木」の篆書の形で代用しています",
    "无": "无 は「無」の異体字です（フォントでは「無」を入力しても表示されます）",
    "ソ": WIKIMEDIA_NOTE,
    "ヘ": WIKIMEDIA_NOTE,
    "ム": WIKIMEDIA_NOTE,
    "゛": "濁点・半濁点の付いた字（ガ・パ など）は、フォントでは「カ＋濁点」「ハ＋半濁点」の 2 マスで表示されます",
}


def font(size):
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except OSError:
        return ImageFont.load_default()


def draw_glyph(d, segments, x, y, scale, st=None):
    st = st or svg.Style()
    for s in range(16):
        pts = [(x + px * scale, y + py * scale) for px, py in svg.segment_polygon(s, st)]
        d.polygon(pts, fill=ON if s in segments else OFF)


def render_segments(path):
    st, scale = svg.Style(), 3.0
    w, h = int(st.width * scale), int(st.height * scale)
    im = Image.new("RGB", (w + 40, h + 40), "white")
    d = ImageDraw.Draw(im)
    draw_glyph(d, set(), 20, 20, scale, st)
    f = font(26)
    for s in range(16):
        pts = svg.segment_polygon(s, st)
        cx = sum(p[0] for p in pts) / len(pts) * scale + 20
        cy = sum(p[1] for p in pts) / len(pts) * scale + 20
        d.text((cx, cy), f"{s:X}", font=f, fill=(200, 0, 0), anchor="mm")
    im.save(path)


def groups(charmap):
    def pick(chars):
        return sorted((c for c in charmap if c in chars), key=chars.index)

    digits, kansuji, marks = pick(DIGITS), pick(KANSUJI), pick(MARKS)
    kana = [c for c in charmap if "゠" <= c <= "ヿ" and c not in marks]
    upper = sorted(c for c in charmap if c.isascii() and c.isupper())
    lower = sorted(c for c in charmap if c.isascii() and c.islower())
    used = set(digits) | set(kansuji) | set(marks) | set(kana) | set(upper) | set(lower)
    kanji = [c for c in charmap if c not in used]
    return [
        ("数字（七セグ）", digits), ("漢数字・単位", kansuji), ("カタカナ", kana),
        ("漢字", kanji), ("英大文字", upper), ("英小文字", lower), ("記号", marks),
    ]


def render_charmap(charmap, path, per_row=13, scale=0.55):
    st = svg.Style()
    gw, gh = int(st.width * scale), int(st.height * scale)
    cw, ch = gw + 26, gh + 58
    title_h = 40
    blocks = [(name, chars) for name, chars in groups(charmap) if chars]
    notes = list(dict.fromkeys(NOTES[c] for _, chars in blocks for c in chars if c in NOTES))
    note_h = 30
    height = 20 + sum(title_h + ((len(c) + per_row - 1) // per_row) * ch + 16 for _, c in blocks)
    height += len(notes) * note_h + (10 if notes else 0)
    im = Image.new("RGB", (per_row * cw + 30, height), "white")
    d = ImageDraw.Draw(im)
    f_title, f_char, f_hex = font(22), font(20), font(15)
    f_long = font(14)  # 長い表示名（マイナス・ハイフン など）は隣と重ならないよう小さくする
    y = 20
    for name, chars in blocks:
        d.text((15, y), f"{name}（{len(chars)}字）", font=f_title, fill=INK)
        y += title_h
        for i, c in enumerate(chars):
            r, k = divmod(i, per_row)
            x0, y0 = 15 + k * cw, y + r * ch
            draw_glyph(d, codec.int_to_segments(codec.from_hex(charmap[c])), x0 + 13, y0, scale, st)
            label = LABELS.get(c, c) + ("※" if c in NOTES else "")
            f_label = f_char if len(label) <= 3 else f_long
            d.text((x0 + cw / 2, y0 + gh + 6), label, font=f_label, fill=INK, anchor="mt")
            d.text((x0 + cw / 2, y0 + gh + 32), charmap[c], font=f_hex, fill=SUB, anchor="mt")
        y += ((len(chars) + per_row - 1) // per_row) * ch + 16
    for note in notes:
        d.text((15, y), f"※ {note}", font=f_hex, fill=INK)
        y += note_h
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("charmap", nargs="?", default=str(ROOT / "data" / "charmap.json"))
    ap.add_argument("-o", "--outdir", default=str(ROOT / "docs"))
    args = ap.parse_args()

    charmap = json.loads(Path(args.charmap).read_text())
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    render_segments(outdir / "segments.png")
    render_charmap(charmap, outdir / "charmap.png")
    print(f"{outdir / 'segments.png'}, {outdir / 'charmap.png'}")


if __name__ == "__main__":
    main()
