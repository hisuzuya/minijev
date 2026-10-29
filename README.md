# minijev

TypeSafe AI の判断モデル **Jev** のような「型付きの判断（選択肢＋確率）」を、小さなローカル LLM の **次トークン確率だけ** で再現する約50行の実験コードです。あわせて、本物の Jev・Opus 5.5（JSON スキーマ固定）と同じ問題（30問・100問）で比べた評価スクリプトと結果を置いています。

2026-10-29「AI駆動開発【大阪支部 Jev特別会】」の LT「Jev の中身は50行で再現できる。でも本物との差はどこにあるのか」で使ったコードです。

🎤 スライド（Speaker Deck）: https://speakerdeck.com/hisuzuya/jev-no-nakami-ha-50-kudari-de-saigen-dekiru-demo-honmono-tono-sa-ha-doko-ni-aru-no-ka


## スライド

全31枚（28枚目までが本編、29枚目からが付録）。下に並べた画像は Speaker Deck と同じ内容です。

<img src="slides/images/slide-01.jpg" width="800" alt="スライド 1">

<details>
<summary>2枚目以降を表示（全31枚）</summary>

<img src="slides/images/slide-02.jpg" width="800" alt="スライド 2">
<img src="slides/images/slide-03.jpg" width="800" alt="スライド 3">
<img src="slides/images/slide-04.jpg" width="800" alt="スライド 4">
<img src="slides/images/slide-05.jpg" width="800" alt="スライド 5">
<img src="slides/images/slide-06.jpg" width="800" alt="スライド 6">
<img src="slides/images/slide-07.jpg" width="800" alt="スライド 7">
<img src="slides/images/slide-08.jpg" width="800" alt="スライド 8">
<img src="slides/images/slide-09.jpg" width="800" alt="スライド 9">
<img src="slides/images/slide-10.jpg" width="800" alt="スライド 10">
<img src="slides/images/slide-11.jpg" width="800" alt="スライド 11">
<img src="slides/images/slide-12.jpg" width="800" alt="スライド 12">
<img src="slides/images/slide-13.jpg" width="800" alt="スライド 13">
<img src="slides/images/slide-14.jpg" width="800" alt="スライド 14">
<img src="slides/images/slide-15.jpg" width="800" alt="スライド 15">
<img src="slides/images/slide-16.jpg" width="800" alt="スライド 16">
<img src="slides/images/slide-17.jpg" width="800" alt="スライド 17">
<img src="slides/images/slide-18.jpg" width="800" alt="スライド 18">
<img src="slides/images/slide-19.jpg" width="800" alt="スライド 19">
<img src="slides/images/slide-20.jpg" width="800" alt="スライド 20">
<img src="slides/images/slide-21.jpg" width="800" alt="スライド 21">
<img src="slides/images/slide-22.jpg" width="800" alt="スライド 22">
<img src="slides/images/slide-23.jpg" width="800" alt="スライド 23">
<img src="slides/images/slide-24.jpg" width="800" alt="スライド 24">
<img src="slides/images/slide-25.jpg" width="800" alt="スライド 25">
<img src="slides/images/slide-26.jpg" width="800" alt="スライド 26">
<img src="slides/images/slide-27.jpg" width="800" alt="スライド 27">
<img src="slides/images/slide-28.jpg" width="800" alt="スライド 28">
<img src="slides/images/slide-29.jpg" width="800" alt="スライド 29">
<img src="slides/images/slide-30.jpg" width="800" alt="スライド 30">
<img src="slides/images/slide-31.jpg" width="800" alt="スライド 31">

</details>

> 本リポジトリは TypeSafe AI とは無関係の個人の実験です。

## しくみ

LLM は「次に来る1語（トークン）」の確率を全語彙について出しています。minijev は文章を生成させず、

1. 選択肢に A / B / C… の記号を振ったプロンプトを1回だけモデルに通す（forward 1回）
2. 次トークンの確率から A / B / C の行だけを取り出す
3. 合計が1になるよう正規化して、答えと確信度にする

だけで、Jev と同じ形（`state` ＋ 名前付き `questions` → noul / choice / score）の結果を返します。Qwen3 の thinking は無効化しています（有効だと最初のトークンが `<think>` になるため）。

## 使い方（Apple Silicon Mac）

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python mlx-lm
.venv/bin/python minijev.py                     # サンプル判定（Qwen3 1.7B 4bit）
MINIJEV_MODEL=mlx-community/Qwen3-4B-4bit .venv/bin/python minijev.py
```

評価（任意）:

```bash
.venv/bin/python eval.py --only minijev         # 自作版
TYPESAFE_API_KEY=... .venv/bin/python eval.py --only jev   # 本物の Jev（有料 API）
CLAUDE_BIN=claude .venv/bin/python eval.py --only opus     # Opus 5.5（claude CLI の --json-schema）
.venv/bin/python metrics.py                     # 運用指標の集計

# 100問版（結果は results/v2/）
.venv/bin/python eval.py --evalset evalset_v2.json --only minijev
.venv/bin/python metrics.py --dir results/v2 --evalset evalset_v2.json
```

## ファイル

| ファイル | 内容 |
|---|---|
| `minijev.py` | 本体（53行）。MLX ＋ Qwen3 で次トークン確率を読む |
| `evalset.json` | 自作の評価セット30問（基本10・否定/複合条件5・数値5・日付5・多選択肢5）。正解は手で付けた |
| `evalset_v2.json` | 100問版（30問＋新規70問、カテゴリの比率は同じ） |
| `eval.py` | 自作版・本物の Jev・Opus 5.5 に同じ問題を解かせる（`--evalset` で問題を切り替え） |
| `metrics.py` | 「確信度0.7以上は自動処理、未満は人に回す」運用での内訳・Brier スコア・95%信頼区間・カテゴリ別の正答を集計 |
| `results/` | 30問の実行結果（2026-10-28）。`SCALE.md` はモデルサイズ（1.7B〜14B）の比較 |
| `results/v2/` | 100問の実行結果（2026-10-28〜29）。`SUMMARY.md` にまとめ |

## 結果：30問（2026-10-28、各1回）

当てずっぽうの期待正答数: 10.5 / 30

| | 正答 | 人に回す | 自動で正解 | 自動で誤り（事故） | Brier | 10問まとめて |
|---|---|---|---|---|---|---|
| 自作 1.7B（Qwen3 1.7B 4bit） | 17/30 | 0 | 17 | 13 | 0.418 | 3.1 秒 |
| 自作 4B（Qwen3 4B 4bit） | 25/30 | 1 | 24 | 5 | 0.171 | 4.9 秒 |
| 本物の Jev（jev-latest） | 27/30 | 3 | 27 | 0 | 0.021 | 0.21 秒 |
| Opus 5.5 ＋ JSON スキーマ | 30/30 | 1 | 29 | 0 | 0.012 | 3.4 秒 |

- 自作 4B は外した5問すべてで確信度 0.99 以上（自信満々で外す）。Jev は外した3問とも 0.55 未満で、閾値で人に回せる。
- 差は正答率よりも「確信度の正しさ」と「質問をまとめて評価する速さ」に出た。

## 結果：100問・14B まで（2026-10-28〜29、各1回）

当てずっぽうの期待正答数: 34.8 / 100。かっこ内は問題を復元抽出したブートストラップの95%信頼区間。

| | 正答 | 自動で誤り（事故） | 外した問題の確信度（中央値） | Brier | 10問まとめて |
|---|---|---|---|---|---|
| 自作 1.7B | 61（51〜70%） | 38 | 1.00 | 0.366 | 3.5 秒 |
| 自作 4B | 80（72〜88%） | 17 | 1.00 | 0.174 | 5.8 秒 |
| 自作 8B | 85（78〜92%） | 12 | 1.00 | 0.116 | 12.9 秒 |
| 自作 14B | 82（74〜89%） | 15 | 1.00 | 0.160 | 16.3 秒 |
| 本物の Jev | 92（87〜97%） | 2 | 0.61 | 0.049 | 0.17 秒 |
| Opus 5.5 ＋ JSON スキーマ | 100 | 0 | — | 0.006 | 3.3 秒 |

- モデルを大きくすると正答率は 4B までは大きく伸びるが、その先は 8B 85・14B 82 で頭打ち。14B でも Jev に届かない。
- 外したときの確信度は 1.7B〜14B すべて中央値 1.00 のままで、事故は 4B〜14B で 12〜17件とほぼ減らない。「自信満々で外す」はサイズでは治らなかった。
- 自作版の誤りは数値（税込計算・合計・割合）と日付（曜日・営業日）に集中する。答えを1語目で出すので途中の計算を書けないため。

### 注意

- 自作の合成データ（30問・100問）・各1回の小さな実験です。傾向であって結論ではありません。
- 自作版は確信度の補正（温度スケーリングなど）を試していません。
- 速度の条件はそろえていません（Jev は日本からの API 往復込み、自作は M4 ローカル、Opus は API 時間）。
- Opus の確信度は自己申告、費用は claude CLI の定価見積もりです。

## License

MIT
