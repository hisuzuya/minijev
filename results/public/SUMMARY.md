# minijev 評価：公開データセット 300 問

- 評価セット: `evalset_public.json`（`build_public.py` で再生成、乱数 seed 0）。公開データセット 6 種から 50 問ずつ
- 実行: 2026-10-29、Apple M4 32GB。自作は `mlx-community/Qwen3-*-4bit`、Jev は `jev-latest`、Opus 5.5 は claude CLI の `--json-schema`（`--effort low`、選択肢の並び替えテストは省略）
- 再現: `.venv/bin/python build_public.py` → `.venv/bin/python eval.py --evalset evalset_public.json [--only minijev|jev|opus]` → `.venv/bin/python metrics.py --dir results/public --evalset evalset_public.json`
- 95% 信頼区間は問題を復元抽出するブートストラップ（10,000 回）
- でたらめに選んだときの期待正答数: 78 / 300

| データ | 何を見るか | 形式 | 抜き出し方 |
|---|---|---|---|
| WRIME | SNS 投稿の感情 | ポジティブ／ネガティブ／どちらでもない | test のうち読者 3 人の極性が一致した投稿 |
| livedoor ニュースコーパス | 記事の分類 | 9 カテゴリ | 全記事（タイトル＋本文先頭 300 字） |
| JNLI（JGLUE v1.3） | 含意関係 | 含意／中立／矛盾 | test |
| Jamp | 時間表現の推論 | 含意／中立／矛盾 | test_2 |
| JCommonsenseQA（JGLUE v1.3） | 常識 | 5 択 | test |
| JMMLU | 数学・ビジネス知識 | 4 択 | 初等数学 25 問＋経営・マーケティング・会計・企業倫理 25 問 |

## ① 正答率

| エンジン | 正答（300問） | 95%CI | WRIME | livedoor | JNLI | Jamp | JCQA | JMMLU |
|---|---|---|---|---|---|---|---|---|
| 自作 1.7B | 137（46%） | 40〜51% | 32 | 25 | 19 | 15 | 25 | 21 |
| 自作 4B | 178（59%） | 54〜65% | 35 | 25 | 31 | 20 | 45 | 22 |
| 自作 8B | 192（64%） | 59〜69% | 38 | 23 | 36 | 27 | 47 | 21 |
| Jev | 245（82%） | 77〜86% | 42 | 33 | 40 | 39 | 48 | 43 |
| Opus 5.5 | 267（89%） | 85〜92% | 44 | 41 | 43 | 44 | 49 | 46 |

（カテゴリ別は各 50 問中の正答数）

## ② 外したときの確信度

| エンジン | 誤答数 | 誤答の確信度 中央値 | 誤答のうち 0.99 以上 | 誤答のうち 0.9 以上 |
|---|---|---|---|---|
| 自作 1.7B | 163 | 0.98 | 66（40%） | 119（73%） |
| 自作 4B | 122 | 0.86 | 34（28%） | 55（45%） |
| 自作 8B | 108 | 0.96 | 47（44%） | 71（66%） |
| Jev | 55 | 0.67 | 2（4%） | 14（25%） |
| Opus 5.5 | 33 | 0.60 | 0（0%） | 2（6%） |

## ③ 確信度の帯ごとの正答率

「この確信度で答えたとき、実際に何 % 当たったか」。確信度が正しければ、帯の値と正答率が近くなる。

| エンジン | 0.7 未満 | 0.7〜0.9 | 0.9〜0.99 | 0.99 以上 |
|---|---|---|---|---|
| 自作 1.7B | 7/24（29%） | 9/36（25%） | 23/76（30%） | 98/164（60%） |
| 自作 4B | 15/54（28%） | 21/49（43%） | 22/43（51%） | 120/154（78%） |
| 自作 8B | 12/30（40%） | 20/39（51%） | 33/57（58%） | 127/174（73%） |
| Jev | 43/72（60%） | 40/52（77%） | 62/74（84%） | 100/102（98%） |
| Opus 5.5 | 38/55（69%） | 85/99（86%） | 131/133（98%） | 13/13（100%） |

### 確信度 0.8 以上で答えた問題の正答率

「確信度 0.8 以上なら自動処理」としたときに、自動処理される問題がどれだけ当たっているか。

| エンジン | 0.8 以上の正答率 | 0.8 以上で答えた割合 | 参考: 自作の問題 100 問 |
|---|---|---|---|
| 自作 1.7B | 48%（127/262） | 87% | 62% |
| 自作 4B | 69%（149/217） | 72% | 83% |
| 自作 8B | 68%（175/257） | 86% | 90% |
| Jev | **91%**（188/207） | 69% | 98% |
| Opus 5.5 | **96%**（214/224） | 75% | 100% |

自作 8B は 4B より正答率が高いが、0.8 以上と答える問題が多いため、絞った後の正答率は 4B と変わらない。

## 結論

- **確信度の当たり具合の差は、公開データでもはっきり残った。** Jev が「0.99 以上」と答えた 102 問は 98% 正解。自作 8B は 174 問で 73%、4B は 154 問で 78%。自作の誤答の 3〜4 割は確信度 0.99 以上で、Jev は 4%。
- **正答率は、自作の問題で見えたほど近くない。** 自作 4B は 59%、8B は 64% で、Jev の 82% とは区間も重ならない。自作の問題（100 問）では 4B 80%・Jev 92% だったので、差は 12 → 23 ポイントに広がった。特に記事分類・時間の推論・JMMLU で差が大きい。
- **Jev・Opus も満点ではない。** Jev の正答は 82%、確信度 0.7 以上での誤答は 26 件（約 9%）。「Jev なら外さない」ではなく「Jev は外すときに迷っていることが多い」が正確。
- **速度**: 同じ状況に 10 問まとめて聞くと、Jev 0.19 秒、自作 4B 3.1 秒、8B 5.7 秒、Opus 6.0 秒。
- **注意**: 公開データは Qwen3・Opus・Jev の学習データに含まれている可能性がある。WRIME は感情の受け取り方に幅があり、Opus でも 6 問外した。

## 付録: 確信度 0.7 で区切った運用の内訳

確信度 0.7 以上は自動処理、未満は人に回す、とした場合の数え直し（③から機械的に決まる）。

| エンジン | 人に回す | 自動で正解 | 自動で誤り（事故） | 事故率 95%CI |
|---|---|---|---|---|
| 自作 1.7B | 24 | 130 | 146 | 43〜54% |
| 自作 4B | 54 | 163 | 83 | 23〜33% |
| 自作 8B | 30 | 180 | 90 | 25〜35% |
| Jev | 72 | 202 | 26 | 6〜12% |
| Opus 5.5 | 55 | 229 | 16 | 3〜8% |

## 出典

各データの公式リポジトリに記載された引用表記に従う。

- **WRIME**（ver.2）— https://github.com/ids-cv/wrime 、CC BY-NC-ND 4.0
  - Tomoyuki Kajiwara, Chenhui Chu, Noriko Takemura, Yuta Nakashima, Hajime Nagahara. WRIME: A New Dataset for Emotional Intensity Estimation with Subjective and Objective Annotations. NAACL 2021, pp.2095-2104.
  - Haruya Suzuki, Yuto Miyauchi, Kazuki Akiyama, Tomoyuki Kajiwara, Takashi Ninomiya, Noriko Takemura, Yuta Nakashima, Hajime Nagahara. A Japanese Dataset for Subjective and Objective Sentiment Polarity Classification in Micro Blog Domain. LREC 2022, pp.7022-7028.
- **livedoor ニュースコーパス** — 株式会社ロンウイット配布 https://www.rondhuit.com/download.html 、記事は CC BY-ND 2.1 JP（NHN Japan 株式会社 livedoor ニュース）
- **JGLUE**（JNLI・JCommonsenseQA、v1.3）— https://github.com/yahoojapan/JGLUE 、CC BY-SA 4.0
  - Kentaro Kurihara, Daisuke Kawahara, Tomohide Shibata. JGLUE: Japanese General Language Understanding Evaluation. LREC 2022.
  - 栗原健太郎, 河原大輔, 柴田知秀. JGLUE: 日本語言語理解ベンチマーク. 言語処理学会第28回年次大会, 2022.
- **Jamp** — https://github.com/tomo-vv/temporalNLI_dataset 、CC BY-SA 4.0
  - Tomoki Sugimoto, Yasumasa Onoe, Hitomi Yanaka. Jamp: Controlled Japanese Temporal Inference Dataset for Evaluating Generalization Capacity of Language Models. ACL 2023 Student Research Workshop, pp.57-68.
- **JMMLU** — https://github.com/nlp-waseda/JMMLU 、CC BY-NC-ND 4.0
  - Ziqi Yin, Hao Wang, Kaito Horio, Daisuke Kawahara, Satoshi Sekine. Should We Respect LLMs? A Cross-Lingual Study on the Influence of Prompt Politeness on LLM Performance. SICon 2024（Second Workshop on Social Influence in Conversations）.
  - 元の MMLU: Dan Hendrycks et al. Measuring Massive Multitask Language Understanding. ICLR 2021.

WRIME・livedoor・JMMLU は改変・再配布禁止（ND）または非営利（NC）のライセンス。問題文を含む `evalset_public.json` と元データの `data/` は公開リポジトリに置かない。
