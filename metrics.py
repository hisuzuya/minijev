"""results/*.json から「どれだけ良いか」の物差しを出す。

使い方: .venv/bin/python metrics.py [--dir results/v2] [--evalset evalset_v2.json]
（既定は results/ と evalset.json）

- でたらめ回答の期待正答数（選択肢数の逆数の合計）
- 閾値 0.7 で運用したとき: 人に回す数 / 自動で通して正解 / 自動で通して誤り（事故）
- Brier スコア: (確信度 - 正解なら1・誤りなら0)^2 の平均。0 が理想、小さいほど確信度が当たっている
- 正答率と事故率の 95% 信頼区間（問題を復元抽出するブートストラップ）
- カテゴリ別の正答率と、外した問題の確信度
"""
import json
import random
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).parent
THRESHOLD = 0.7
BOOT = 10000  # ブートストラップの反復回数


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def ci95(rows, stat):
    """問題を復元抽出して stat を計算し、2.5% / 97.5% 点を返す。"""
    rng = random.Random(0)
    vals = sorted(stat(rng.choices(rows, k=len(rows))) for _ in range(BOOT))
    return vals[int(BOOT * 0.025)], vals[int(BOOT * 0.975)]


def accuracy(rows):
    return sum(r["correct"] for r in rows) / len(rows)


def accident_rate(rows):
    return sum(not r["correct"] and r["confidence"] >= THRESHOLD for r in rows) / len(rows)


def pct(lo_hi):
    return f"{lo_hi[0]:.0%}〜{lo_hi[1]:.0%}"


DIR = HERE / arg("--dir", "results")
ITEMS = json.loads((HERE / arg("--evalset", "evalset.json")).read_text())
N = len(ITEMS)
results = {p.stem: json.loads(p.read_text()) for p in sorted(DIR.glob("*.json"))}

random_hits = sum(1 / (2 if it["q"]["type"] == "noul" else len(it["q"]["options"])) for it in ITEMS)
print(f"でたらめに選んだときの期待正答数: {random_hits:.1f} / {N}\n")
print("| エンジン | 正答 | 正答率 95%CI | 人に回す | 自動で正解 | 自動で誤り（事故） | 事故率 95%CI | Brier | 1問 p50 | 10問 | 費用/問 |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for name, res in results.items():
    rows = res["rows"]
    assert len(rows) == N, f"{name}: {len(rows)} 問（評価セットは {N} 問）"
    routed = [r for r in rows if r["confidence"] < THRESHOLD]
    auto = [r for r in rows if r["confidence"] >= THRESHOLD]
    brier = statistics.mean((r["confidence"] - r["correct"]) ** 2 for r in rows)
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    cost = f"${statistics.mean(costs):.4f}" if costs else "-"
    print(f"| {name} | {sum(r['correct'] for r in rows)}/{N} | {pct(ci95(rows, accuracy))} | {len(routed)} | "
          f"{sum(r['correct'] for r in auto)} | {sum(not r['correct'] for r in auto)} | {pct(ci95(rows, accident_rate))} | "
          f"{brier:.3f} | {statistics.median(r['latency_ms'] for r in rows):.0f}ms | {res['scaling_ms']['10']:.0f}ms | {cost} |")

cats = list(dict.fromkeys(it["category"] for it in ITEMS))
print("\n### カテゴリ別の正答\n")
print("| エンジン | " + " | ".join(f"{c}（{sum(it['category'] == c for it in ITEMS)}）" for c in cats) + " |")
print("|---" * (len(cats) + 1) + "|")
for name, res in results.items():
    rows = res["rows"]
    print(f"| {name} | " + " | ".join(str(sum(r["correct"] for r in rows if r["category"] == c)) for c in cats) + " |")

print("\n### 外した問題の確信度\n")
print("| エンジン | 誤答数 | 誤答の確信度 中央値 | 誤答のうち 0.99 以上 | 誤答のうち 0.7 未満（人に回る） | 並び替えで答えが同じ |")
print("|---|---|---|---|---|---|")
for name, res in results.items():
    rows = res["rows"]
    wrong = [r["confidence"] for r in rows if not r["correct"]]
    shuf = [r for r in rows if "order_stable" in r]
    med = f"{statistics.median(wrong):.2f}" if wrong else "-"
    print(f"| {name} | {len(wrong)} | {med} | {sum(c >= 0.99 for c in wrong)} | {sum(c < THRESHOLD for c in wrong)} | "
          f"{sum(r['order_stable'] for r in shuf)}/{len(shuf)} |")
