# minijev

TypeSafe AI の判断モデル **Jev** のような「型付きの判断（選択肢＋確率）」を、小さなローカル LLM の **次トークン確率だけ** で再現する約50行の実験コードです。あわせて、本物の Jev・Opus 5.5（JSON スキーマ固定）と同じ30問で比べた評価スクリプトと結果を置いています。

2026-10-29「AI駆動開発【大阪支部 Jev特別会】」の LT「Jev の中身は50行で再現できる。でも本物との差はどこにあるのか」で使ったコードです。

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
```

## ファイル

| ファイル | 内容 |
|---|---|
| `minijev.py` | 本体（53行）。MLX ＋ Qwen3 で次トークン確率を読む |
| `evalset.json` | 自作の評価セット30問（基本10・否定/複合条件5・数値5・日付5・多選択肢5）。正解は手で付けた |
| `eval.py` | 自作版・本物の Jev・Opus 5.5 に同じ30問を解かせる |
| `metrics.py` | 「確信度0.7以上は自動処理、未満は人に回す」運用での内訳と Brier スコアを集計 |
| `results/` | 2026-10-28 の実行結果 |

## 結果（2026-10-28、各1回）

当てずっぽうの期待正答数: 10.5 / 30

| | 正答 | 人に回す | 自動で正解 | 自動で誤り（事故） | Brier | 10問まとめて |
|---|---|---|---|---|---|---|
| 自作 1.7B（Qwen3 1.7B 4bit） | 17/30 | 0 | 17 | 13 | 0.418 | 3.1 秒 |
| 自作 4B（Qwen3 4B 4bit） | 25/30 | 1 | 24 | 5 | 0.171 | 4.9 秒 |
| 本物の Jev（jev-latest） | 27/30 | 3 | 27 | 0 | 0.021 | 0.21 秒 |
| Opus 5.5 ＋ JSON スキーマ | 30/30 | 1 | 29 | 0 | 0.012 | 3.4 秒 |

- 自作 4B は正答率では Jev に迫るが、外した5問すべてで確信度 0.99 以上（自信満々で外す）。Jev は外した3問とも 0.55 未満で、閾値で人に回せる。
- 差は正答率ではなく「確信度の正しさ」と「質問をまとめて評価する速さ」に出た。

### 注意

- 自作の合成データ30問・各1回の小さな実験です。傾向であって結論ではありません。
- 自作版は確信度の補正（温度スケーリングなど）を試していません。
- 速度の条件はそろえていません（Jev は日本からの API 往復込み、自作は M4 ローカル、Opus は API 時間）。
- Opus の確信度は自己申告、費用は claude CLI の定価見積もりです。

## License

MIT
