"""results/*.json から「どれだけ良いか」の物差しを出す。

- でたらめ回答の期待正答数（選択肢数の逆数の合計）
- 閾値 0.7 で運用したとき: 人に回す数 / 自動で通して正解 / 自動で通して誤り（事故）
- Brier スコア: (確信度 - 正解なら1・誤りなら0)^2 の平均。0 が理想、小さいほど確信度が当たっている
"""
import json
import statistics
from pathlib import Path

HERE = Path(__file__).parent
ITEMS = json.loads((HERE / "evalset.json").read_text())
THRESHOLD = 0.7

random_hits = sum(1 / (2 if it["q"]["type"] == "noul" else len(it["q"]["options"])) for it in ITEMS)
print(f"でたらめに選んだときの期待正答数: {random_hits:.1f} / {len(ITEMS)}\n")
print("| エンジン | 正答 | 人に回す | 自動で正解 | 自動で誤り（事故） | Brier | 1問 p50 | 10問 | 費用/問 |")
print("|---|---|---|---|---|---|---|---|---|")
for path in sorted((HERE / "results").glob("*.json")):
    res = json.loads(path.read_text())
    rows = res["rows"]
    routed = [r for r in rows if r["confidence"] < THRESHOLD]
    auto = [r for r in rows if r["confidence"] >= THRESHOLD]
    brier = statistics.mean((r["confidence"] - r["correct"]) ** 2 for r in rows)
    costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
    cost = f"${statistics.mean(costs):.4f}" if costs else "-"
    print(f"| {path.stem} | {sum(r['correct'] for r in rows)}/30 | {len(routed)} | "
          f"{sum(r['correct'] for r in auto)} | {sum(not r['correct'] for r in auto)} | {brier:.3f} | "
          f"{statistics.median(r['latency_ms'] for r in rows):.0f}ms | {res['scaling_ms']['10']:.0f}ms | {cost} |")
