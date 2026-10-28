"""minijev: Jev 風の「型付き判断」を、小型 LLM の次トークン確率だけで作る超簡易版。

文章は生成しない。選択肢に A/B/C... のラベルを振り、1 回の forward で
次トークンの logit をラベルだけに絞って softmax する。それだけ。
"""
import os
import string
import time

import mlx.core as mx
from mlx_lm import load

MODEL = os.environ.get("MINIJEV_MODEL", "mlx-community/Qwen3-1.7B-4bit")
LABELS = string.ascii_uppercase  # ラベルは 1 トークン → 最大 26 択

model, tok = load(MODEL)
LABEL_IDS = [tok.encode(c, add_special_tokens=False)[0] for c in LABELS]


def _distribution(state, instructions, options):
    """選択肢ごとの確率と、ラベルに乗った確率質量を返す。"""
    labels = LABELS[: len(options)]
    body = "\n".join(f"{l}. {o}" for l, o in zip(labels, options))
    msg = (f"# 状況\n{state}\n\n# 質問\n{instructions}\n\n# 選択肢\n{body}\n\n"
           "最も適切な選択肢の記号を1文字だけ答えてください。")
    prompt = tok.apply_chat_template([{"role": "user", "content": msg}], tokenize=False,
                                     add_generation_prompt=True, enable_thinking=False)
    logits = model(mx.array(tok.encode(prompt, add_special_tokens=False))[None])[0, -1]
    full = mx.softmax(logits.astype(mx.float32))         # 語彙全体の確率
    picked = full[mx.array(LABEL_IDS[: len(options)])]   # ラベルだけ取り出す
    mass = picked.sum().item()
    return dict(zip(options, (picked / mass).tolist())), mass


def ask(state, q):
    """q = {"type": "choice"|"noul"|"score", "instructions": str, "options"|"levels": [...]}"""
    if q["type"] == "noul":
        p, mass = _distribution(state, q["instructions"], ["はい", "いいえ"])
        return {"type": "noul", "noul": p["はい"], "label_mass": mass}
    options = q.get("options") or q["levels"]
    p, mass = _distribution(state, q["instructions"], options)
    best = max(p, key=p.get)
    out = {"type": q["type"], "choice": best, "probabilities": p, "confidence": p[best], "label_mass": mass}
    if q["type"] == "score":  # 段階の確率で重み付けした平均を 0〜1 に
        out["score"] = sum(i * p[o] for i, o in enumerate(options)) / (len(options) - 1)
    return out


def decide(state, questions):
    """Jev の /v1/systemone と同じ形: 1 つの state に複数の名前付き質問。"""
    t = time.perf_counter()
    answers = {name: ask(state, q) for name, q in questions.items()}
    return {"answers": answers, "latency_ms": round((time.perf_counter() - t) * 1000, 1)}


if __name__ == "__main__":
    import json
    print(json.dumps(decide(
        "お客様: 昨日から本番環境にログインできません。今日の15時の商談デモで使う予定です。",
        {
            "urgent": {"type": "noul", "instructions": "至急対応が必要な問い合わせですか？"},
            "category": {"type": "choice", "instructions": "問い合わせの種類は？",
                         "options": ["請求", "障害・不具合", "機能要望", "解約"]},
            "severity": {"type": "score", "instructions": "深刻度は？", "levels": ["低", "中", "高"]},
        }), ensure_ascii=False, indent=2))
