"""公開データセット 6 種から 50 問ずつ抜き出して evalset_public.json を作る。

使い方: .venv/bin/python build_public.py
元データは data/ にダウンロードする（ライセンス上、evalset_public.json と data/ は再配布しない）。

| 名前 | 元データ | ライセンス |
|---|---|---|
| WRIME | ids-cv/wrime（読者 3 人の感情極性。3 人の符号が一致した投稿だけ使う） | CC BY-NC-ND 4.0 |
| livedoor | livedoor ニュースコーパス（9 カテゴリ） | CC BY-ND 2.1 JP |
| JNLI | JGLUE v1.3 test（yahoojapan/JGLUE） | CC BY-SA 4.0 |
| Jamp | 時間表現の推論 test_2（tomo-vv/temporalNLI_dataset） | CC BY-SA 4.0 |
| JCommonsenseQA | JGLUE v1.3 test（yahoojapan/JGLUE） | CC BY-SA 4.0 |
| JMMLU | 初等数学 25 問＋ビジネス系 25 問（nlp-waseda/JMMLU） | CC BY-NC-ND 4.0 |
"""
import csv
import io
import json
import random
import tarfile
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
N = 50
NLI = {"entailment": "正しいと言える（含意）", "neutral": "正しいとも誤りとも言えない（中立）",
       "contradiction": "誤りと言える（矛盾）"}
JGLUE = "https://raw.githubusercontent.com/yahoojapan/JGLUE/main/datasets"
NLI_Q = "前提が正しいとき、仮説はどうなりますか？"
LIVEDOOR = {  # ディレクトリ名 → 選択肢に出す名前
    "dokujo-tsushin": "独女通信（独身女性向けコラム）", "it-life-hack": "ITライフハック（IT・PC活用）",
    "kaden-channel": "家電チャンネル（家電・ガジェット）", "livedoor-homme": "livedoor HOMME（男性向けライフスタイル）",
    "movie-enter": "MOVIE ENTER（映画）", "peachy": "Peachy（女性向けライフスタイル）",
    "smax": "エスマックス（スマートフォン）", "sports-watch": "Sports Watch（スポーツ）", "topic-news": "トピックニュース（時事・話題）",
}


def fetch(url, name):
    """data/ に無ければダウンロードしてパスを返す。"""
    path = DATA / name
    if not path.exists():
        DATA.mkdir(exist_ok=True)
        path.write_bytes(urllib.request.urlopen(url, timeout=120).read())
    return path


def jsonl(url, name):
    return [json.loads(line) for line in fetch(url, name).read_text(encoding="utf-8").splitlines() if line.strip()]


def item(prefix, i, category, state, instructions, options, answer):
    assert answer in options and len(set(options)) == len(options)
    return {"id": f"{prefix}-{i:02d}", "category": category, "state": state,
            "q": {"type": "choice", "instructions": instructions, "options": options}, "answer": answer}


def wrime():
    rows = list(csv.DictReader(fetch("https://raw.githubusercontent.com/ids-cv/wrime/master/wrime-ver2.tsv",
                                     "wrime-ver2.tsv").open(encoding="utf-8"), delimiter="\t"))
    sign = lambda v: (int(v) > 0) - (int(v) < 0)
    pool = []
    for r in rows:
        signs = {sign(r[f"Reader{k}_Sentiment"]) for k in (1, 2, 3)}
        if r["Train/Dev/Test"] == "test" and len(signs) == 1:
            pool.append((r["Sentence"], ["ネガティブ", "どちらでもない", "ポジティブ"][signs.pop() + 1]))
    return [item("wrime", i + 1, "WRIME（感情）", f"SNS投稿: {text}", "この投稿の感情は？",
                 ["ポジティブ", "ネガティブ", "どちらでもない"], ans)
            for i, (text, ans) in enumerate(random.Random(0).sample(pool, N))]


def livedoor():
    tar = tarfile.open(fetch("https://www.rondhuit.com/download/ldcc-20140209.tar.gz", "ldcc-20140209.tar.gz"))
    pool = []
    for m in tar.getmembers():
        parts = Path(m.name).parts  # text/<カテゴリ>/<カテゴリ>-<番号>.txt
        if len(parts) == 3 and parts[1] in LIVEDOOR and parts[2].startswith(parts[1]):
            lines = tar.extractfile(m).read().decode("utf-8").splitlines()
            body = "".join(lines[3:]).strip()[:300]
            pool.append((f"タイトル: {lines[2]}\n本文: {body}", LIVEDOOR[parts[1]]))
    pool.sort()
    return [item("livedoor", i + 1, "livedoor（記事分類）", state, "この記事の掲載カテゴリは？", list(LIVEDOOR.values()), ans)
            for i, (state, ans) in enumerate(random.Random(0).sample(pool, N))]


def nli(prefix, category, rows):
    """rows = [(前提, 仮説, entailment|neutral|contradiction)]"""
    return [item(prefix, i + 1, category, f"前提: {a}\n仮説: {b}", NLI_Q, list(NLI.values()), NLI[label])
            for i, (a, b, label) in enumerate(random.Random(0).sample(rows, N))]


def jnli():
    rows = jsonl(f"{JGLUE}/jnli-v1.3/test-v1.3.json", "jnli-test-v1.3.json")
    return nli("jnli", "JNLI（含意関係）", [(r["sentence1"], r["sentence2"], r["label"]) for r in rows])


def jamp():
    path = fetch("https://raw.githubusercontent.com/tomo-vv/temporalNLI_dataset/main/dataset/test_2.tsv", "jamp-test_2.tsv")
    rows = list(csv.DictReader(path.open(encoding="utf-8"), delimiter="\t"))
    return nli("jamp", "Jamp（時間の推論）", [(r["premise"], r["hypothesis"], r["gold_label"]) for r in rows])


def jcqa():
    rows = random.Random(0).sample(jsonl(f"{JGLUE}/jcommonsenseqa-v1.3/test-v1.3.json", "jcqa-test-v1.3.json"), N)
    return [item("jcqa", i + 1, "JCommonsenseQA（常識）", f"問題: {r['question']}", "最も適切な答えは？",
                 [r[f"choice{k}"] for k in range(5)], r[f"choice{r['label']}"]) for i, r in enumerate(rows)]


def jmmlu():
    z = zipfile.ZipFile(fetch("https://huggingface.co/datasets/nlp-waseda/JMMLU/resolve/main/JMMLU.zip", "JMMLU.zip"))
    read = lambda name: list(csv.DictReader(io.TextIOWrapper(z.open(f"JMMLU/test/{name}.csv"), encoding="utf-8-sig")))
    usable = lambda rows: [r for r in rows if len({r[k].strip() for k in "ABCD"}) == 4]  # 同じ選択肢が並ぶ問題は除く
    rng = random.Random(0)
    math = rng.sample(usable(read("elementary_mathematics")), N // 2)
    biz = rng.sample(usable(sum((read(s) for s in ("management", "marketing", "professional_accounting", "business_ethics")), [])), N - N // 2)
    return [item("jmmlu", i + 1, "JMMLU（数学・ビジネス）", f"問題: {r['question'].strip()}", "正しい答えは？",
                 [r[k].strip() for k in "ABCD"], r[r["answer"].strip()].strip()) for i, r in enumerate(math + biz)]


if __name__ == "__main__":
    items = wrime() + livedoor() + jnli() + jamp() + jcqa() + jmmlu()
    lines = []
    for it in items:  # evalset.json と同じく 1 問 2 行
        head = json.dumps({k: it[k] for k in ("id", "category", "state")}, ensure_ascii=False)[:-1]
        tail = json.dumps({k: it[k] for k in ("q", "answer")}, ensure_ascii=False)[1:]
        lines.append(f"  {head},\n   {tail}")
    (HERE / "evalset_public.json").write_text("[\n" + ",\n".join(lines) + "\n]\n")
    print(f"{len(items)} 問を evalset_public.json に書き出した")
