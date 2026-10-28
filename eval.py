"""評価セット 30 問を minijev と本物の Jev に解かせて比べる。

使い方: .venv/bin/python eval.py [--only minijev|jev|opus]
TypeSafe の API キーは環境変数 TYPESAFE_API_KEY、なければ ~/.config/jev-browser/credentials.env から読む（表示しない）。
claude CLI の場所は環境変数 CLAUDE_BIN で指定できる（既定は PATH 上の claude）。
"""
import json
import os
import random
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
ITEMS = json.loads((HERE / "evalset.json").read_text())
CRED = Path.home() / ".config/jev-browser/credentials.env"
SHUFFLES = 3  # 選択肢の並び替え回数（並び順への強さを見る）


def jev_key():
    if os.environ.get("TYPESAFE_API_KEY"):
        return os.environ["TYPESAFE_API_KEY"]
    for line in (CRED.read_text().splitlines() if CRED.exists() else []):
        if line.startswith("TYPESAFE_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("TYPESAFE_API_KEY が未設定です")


def jev_decide(state, questions):
    """本物の Jev: POST https://api.typesafe.ai/v1/systemone"""
    body = {"model": "jev-latest", "state": state, "questions": {}}
    for name, q in questions.items():
        if q["type"] == "noul":
            body["questions"][name] = {"type": "noul", "instructions": q["instructions"]}
        else:
            body["questions"][name] = {"type": "choice", "instructions": q["instructions"],
                                       "criteria": {o: None for o in q["options"]}}
    req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {jev_key()}", "Content-Type": "application/json"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    return {"answers": res["answers"], "latency_ms": (time.perf_counter() - t) * 1000, "usage": res.get("usage")}


CLAUDE = os.environ.get("CLAUDE_BIN", "claude")  # Opus 5.5 に対応した claude CLI
OPUS_SYSTEM = "あなたは判定器です。与えられた状況と質問に対し、選択肢から1つ選び、その答えが正しい確率を confidence (0〜1) として返します。"


def opus_decide(state, questions):
    """比較用: Opus 5.5 に JSON スキーマで答えの形を固定させる（claude CLI の --json-schema）。"""
    props, lines = {}, []
    for name, q in questions.items():
        options = ["はい", "いいえ"] if q["type"] == "noul" else q["options"]
        props[name] = {"type": "object", "additionalProperties": False, "required": ["answer", "confidence"],
                       "properties": {"answer": {"type": "string", "enum": options},
                                      "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}
        lines.append(f"- {name}: {q['instructions']}（選択肢: {' / '.join(options)}）")
    schema = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    prompt = f"# 状況\n{state}\n\n# 質問\n" + "\n".join(lines)
    cmd = [str(CLAUDE), "-p", "--model", "claude-opus-5-5", "--effort", "low", "--output-format", "json",
           "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands",
           "--system-prompt", OPUS_SYSTEM, "--json-schema", json.dumps(schema, ensure_ascii=False), prompt]
    res = json.loads(subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=180).stdout)
    answers = {}
    for name, q in questions.items():
        a = res["structured_output"][name]
        if q["type"] == "noul":
            p_yes = a["confidence"] if a["answer"] == "はい" else 1 - a["confidence"]
            answers[name] = {"type": "noul", "noul": p_yes}
        else:
            answers[name] = {"type": "choice", "choice": a["answer"], "confidence": a["confidence"]}
    # CLI の起動時間を除いた API 時間で比べる
    return {"answers": answers, "latency_ms": res["duration_api_ms"], "cost_usd": res["total_cost_usd"]}


def to_pred(ans):
    """回答を (予測ラベル, 確信度) にそろえる。noul は 0.5 で切る。"""
    if ans["type"] == "noul":
        p = ans["noul"]
        return ("はい" if p >= 0.5 else "いいえ"), max(p, 1 - p)
    return ans["choice"], ans["confidence"]


def run(engine, decide):
    rows = []
    decide(ITEMS[0]["state"], {"q": ITEMS[0]["q"]})  # ウォームアップ（初回のコンパイル・接続を除く）
    for it in ITEMS:
        r = decide(it["state"], {"q": it["q"]})
        pred, conf = to_pred(r["answers"]["q"])
        row = {"id": it["id"], "category": it["category"], "answer": it["answer"], "pred": pred,
               "confidence": conf, "correct": pred == it["answer"], "latency_ms": r["latency_ms"],
               "cost_usd": r.get("cost_usd")}
        if it["q"]["type"] == "choice":  # 並び順を変えても同じ答えか
            preds = []
            for s in range(SHUFFLES):
                opts = it["q"]["options"][:]
                random.Random(s).shuffle(opts)
                preds.append(to_pred(decide(it["state"], {"q": {**it["q"], "options": opts}})["answers"]["q"])[0])
            row["shuffle_preds"] = preds
            row["order_stable"] = all(p == pred for p in preds)
        rows.append(row)
        print(f"[{engine}] {it['id']:9} {'○' if row['correct'] else '×'} {pred} ({conf:.2f}) {r['latency_ms']:.0f}ms", flush=True)

    # 同じ state に質問を 1 / 5 / 10 個投げたときの応答時間
    base = ITEMS[0]
    scaling = {}
    for n in (1, 5, 10):
        qs = {f"q{i}": base["q"] for i in range(n)}
        scaling[n] = statistics.median(decide(base["state"], qs)["latency_ms"] for _ in range(3))
    return {"rows": rows, "scaling_ms": scaling}


def summarize(engine, res):
    rows = res["rows"]
    acc = lambda rs: f"{sum(r['correct'] for r in rs)}/{len(rs)}"
    lines = [f"## {engine}", "", f"- 正答: {acc(rows)}"]
    for cat in dict.fromkeys(r["category"] for r in rows):
        lines.append(f"  - {cat}: {acc([r for r in rows if r['category'] == cat])}")
    lines.append(f"- 1問あたり p50: {statistics.median(r['latency_ms'] for r in rows):.0f}ms")
    lines.append("- 同じ state への質問数と応答時間(p50): " + ", ".join(f"{n}問 {ms:.0f}ms" for n, ms in res["scaling_ms"].items()))
    lines.append("- 確信度の帯ごとの正答率:")
    for lo, hi in ((0, 0.7), (0.7, 0.9), (0.9, 0.99), (0.99, 1.01)):
        b = [r for r in rows if lo <= r["confidence"] < hi]
        if b:
            lines.append(f"  - {lo:.2f}〜{min(hi, 1):.2f}: {acc(b)}（平均確信度 {statistics.mean(r['confidence'] for r in b):.2f}）")
    shuf = [r for r in rows if "order_stable" in r]
    lines.append(f"- 選択肢の並びを変えても答えが同じ: {sum(r['order_stable'] for r in shuf)}/{len(shuf)}")
    wrong = [f"{r['id']}（正解 {r['answer']} → {r['pred']} {r['confidence']:.2f}）" for r in rows if not r["correct"]]
    lines.append("- 間違えた問題: " + ("、".join(wrong) or "なし"))
    return "\n".join(lines)


if __name__ == "__main__":
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    engines = {}
    if only in (None, "minijev"):
        from minijev import MODEL, decide as mini_decide
        engines[f"minijev-{MODEL.split('/')[-1]}"] = mini_decide
    if only in (None, "jev"):
        engines["jev"] = jev_decide
    if only in (None, "opus"):
        engines["opus-5.5-structured"] = opus_decide
    for name, fn in engines.items():
        res = run(name, fn)
        (out / f"{name}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
        summary = summarize(name, res)
        (out / f"{name}.md").write_text(summary + "\n")
        print(summary)
