# 16segmen_font
漢数字をデジタルで表示する仕組みをフォントにしてみる
デジタルのアラビア数字は日の字で配列された8セグメントで表示するように、イギリス国旗（米文字に田文字を被る）で配列された16セグメントで漢数字や簡単な漢字を表示する仕組みに拡張して、ついでにパソコンフォントにしてみる。

##PART1 記号化
1. 16セグメントを5*5の行列をベースにする。四隅と一番上下中央などセグメントが存在しない部分をマスク。手書きの画像を読み込んで要素ごとを0/1で記録する。
2. 16セグメントに1~9A~Gと位置で番号を振って、行列を16桁の2進数に変換する。
3. 16進数を数字に変換して、文字:対応する数字　というふうに対照リストを作って保存する。

##PART2 復号
1. 逆プロセスで文字に対応する行列を生成
2. 行列からSVGファイルを描画、SVG化時セグメント一本ごとセグメントの形にしたい <==>
3. 最初の手書き画像とSVGの一致性をAIで判別

##PART3 OTF化
各文字のSVGファイルからフォントファイルOTFを生成

## セグメント番号

手書きの配置図: `samples/segment_layout.jpg`。5×5 行列の位置は次のとおり（`.` はマスク）。

```
.  0  .  1  .
2  3  4  5  6
.  7  .  8  .
9  A  B  C  D
.  E  .  F  .
```

16bit 化するときは、セグメント 0 を最上位ビット（`0x8000`）、F を最下位ビット（`0x0001`）にする。例: 一 = 7, 8 → `0180`。

## 使い方

```bash
. ~/pydev/bin/activate
python -m unittest                                  # テスト
python scripts/evaluate.py data/kansuji_truth.json  # 手書き画像の読み取り結果を正解データと照合
python scripts/encode.py data/kansuji_truth.json    # PART1: data/charmap.json を生成
python scripts/decode.py                            # PART2: svg/<文字>.svg と svg/index.html を生成
```

シート定義 JSON（例: `data/kansuji_truth.json`）には、画像パス `image`、行ごとの文字列 `rows`、
評価用の正解 `segments`（点灯セグメント番号の列挙）を書く。

