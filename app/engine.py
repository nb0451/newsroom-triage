"""The working parts. Option A never needs to read this file."""
import os, re, json, time, sqlite3, pathlib, math
from dataclasses import dataclass, field, asdict
from typing import Optional

from . import config

HERE = pathlib.Path(__file__).parent
DB_PATH = os.environ.get("TRIAGE_DB", str(HERE.parent / "triage.db"))
CATS = ["World", "Sports", "Business", "Sci/Tech"]


# ---------------------------------------------------------------- storage
def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            headline TEXT NOT NULL,
            branch TEXT NOT NULL,
            answer TEXT,
            confidence REAL,
            passages TEXT,
            guardrails TEXT,
            blocked INTEGER NOT NULL DEFAULT 0,
            mode TEXT NOT NULL,
            ms INTEGER NOT NULL)""")


# -------------------------------------------------------------- retrieval
def _tokens(s):
    return re.findall(r"[a-z0-9]+", str(s).lower())

def _chunks():
    """Each heading section of each switched-on file is one passage."""
    out = []
    for name in config.KNOWLEDGE_FILES:
        p = HERE / "knowledge" / name
        if not p.exists():
            continue
        current, buf = "(top)", []
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                if buf:
                    out.append((name, current, " ".join(buf).strip()))
                current, buf = line.lstrip("# ").strip(), []
            else:
                buf.append(line)
        if buf:
            out.append((name, current, " ".join(buf).strip()))
    return [c for c in out if c[2]]

def retrieve(question):
    """Plain keyword overlap. Deliberately simple so its failures are visible."""
    q = set(_tokens(question))
    if not q:
        return []
    scored = []
    for fname, heading, body in _chunks():
        b = set(_tokens(heading + " " + body))
        if not b:
            continue
        score = len(q & b) / math.sqrt(len(b))
        if score >= config.KNOWLEDGE_THRESHOLD:
            scored.append({"file": fname, "heading": heading,
                           "text": body[:400], "score": round(score, 3)})
    scored.sort(key=lambda d: -d["score"])
    return scored[: config.KNOWLEDGE_PASSAGES]


# ---------------------------------------------------------------- routing
def route(question):
    low = str(question).lower()
    for phrase, branch in config.ROUTING_RULES:
        if phrase.lower() in low:
            return branch, f'matched the rule "{phrase}"'
    return "classify", "no rule matched, so the default branch was used"


# ------------------------------------------------------------ model call
def _demo_classify(text):
    """Used when there is no API key. A deliberately dumb stand-in."""
    hints = {
        "Sports":   ["match", "cup", "olympic", "coach", "league", "striker",
                     "goal", "season", "tournament", "championship", "player"],
        "Business": ["profit", "shares", "market", "bank", "earnings", "deal",
                     "economy", "prices", "revenue", "merger", "billion"],
        "Sci/Tech": ["software", "chip", "nasa", "research", "scientists",
                     "space", "internet", "microsoft", "technology", "study"],
        "World":    ["president", "minister", "troops", "election", "talks",
                     "killed", "government", "united nations", "border"],
    }
    toks = set(_tokens(text))
    best, score = "World", 0
    for cat, words in hints.items():
        hit = len(toks & set(words))
        if hit > score:
            best, score = cat, hit
    conf = min(0.35 + 0.15 * score, 0.95)
    return best, round(conf, 2)

def _groq_classify(text, prompt, passages):
    import requests
    key = os.environ["GROQ_API_KEY"]
    context = ""
    if passages:
        context = "\n\nYou may use these notes:\n" + "\n".join(
            f"- {p['heading']}: {p['text']}" for p in passages)
    body = {
        "model": config.MODEL,
        "temperature": config.TEMPERATURE,
        "max_tokens": 80,
        "messages": [
            {"role": "system", "content": prompt + context},
            {"role": "user", "content":
             f"News item:\n{text}\n\n"
             'Reply with JSON only: {"category": "...", "confidence": 0.0}'},
        ],
    }
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                      headers={"Authorization": f"Bearer {key}"},
                      json=body, timeout=60)
    if r.status_code == 429:
        raise RuntimeError(r.headers.get("retry-after", "0"))
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]
    return _parse(raw)

def _parse(raw):
    """Models wrap JSON in prose and fences. Get the category out anyway."""
    s = str(raw).strip()
    m = re.search(r"\{.*\}", s, re.S)
    if m:
        try:
            d = json.loads(m.group(0))
            cat = str(d.get("category", "")).strip()
            conf = float(d.get("confidence", 0.5))
            for c in CATS:
                if cat.lower() == c.lower():
                    return c, max(0.0, min(1.0, conf))
        except Exception:
            pass
    low = s.lower()
    for c in CATS:
        if c.lower() in low:
            return c, 0.5
    if "sci" in low or "tech" in low:
        return "Sci/Tech", 0.5
    return "UNPARSED", 0.0

def live_mode():
    return bool(os.environ.get("GROQ_API_KEY"))


# ------------------------------------------------------------- guardrails
def check(answer, confidence, branch):
    results = []
    low = str(answer).lower()

    hit = [p for p in config.BANNED_PHRASES if p.lower() in low]
    results.append({"name": "no banned phrase", "passed": not hit,
                    "detail": f"found {hit}" if hit else "none found",
                    "blocking": True})

    ok_cat = branch != "classify" or answer in config.ALLOWED_CATEGORIES
    results.append({"name": "answer is one of the four", "passed": ok_cat,
                    "detail": answer if not ok_cat else "yes",
                    "blocking": True})

    sure = confidence >= config.CONFIDENCE_FLOOR
    results.append({"name": "confident enough", "passed": sure,
                    "detail": f"{confidence:.2f} against floor {config.CONFIDENCE_FLOOR:.2f}",
                    "blocking": True})

    substantial = len(str(answer).strip()) > 0
    results.append({"name": "answer is not empty", "passed": substantial,
                    "detail": f"{len(str(answer).strip())} characters",
                    "blocking": True})
    return results


# ------------------------------------------------------------------- run
@dataclass
class Trace:
    headline: str
    branch: str = ""
    why_branch: str = ""
    passages: list = field(default_factory=list)
    raw_answer: str = ""
    confidence: float = 0.0
    guardrails: list = field(default_factory=list)
    blocked: bool = False
    final: str = ""
    mode: str = "demo"
    ms: int = 0

SAFE = "I am not able to answer that one."

def classify(headline):
    t0 = time.time()
    tr = Trace(headline=str(headline))
    tr.mode = "live" if live_mode() else "demo"

    if not str(headline).strip():
        tr.branch, tr.why_branch = "refuse", "the input was empty"
        tr.final = "Please paste a news headline first."
        tr.guardrails = check(tr.final, 1.0, "refuse")
        tr.ms = int((time.time() - t0) * 1000)
        _save(tr)
        return tr

    tr.branch, tr.why_branch = route(headline)
    tr.passages = retrieve(headline)

    if tr.branch == "refuse":
        tr.final = "I cannot do that. I only sort news items into categories."
        tr.confidence = 1.0
    elif tr.branch == "explain":
        if tr.passages:
            tr.final = ("Here is the rule I follow. "
                        + tr.passages[0]["text"][:220])
        else:
            tr.final = "I do not have a note covering that."
        tr.confidence = 1.0
    else:
        if tr.mode == "live":
            cat, conf = _groq_classify(headline, config.SYSTEM_PROMPT, tr.passages)
        else:
            cat, conf = _demo_classify(headline)
        tr.final, tr.confidence = cat, conf

    tr.raw_answer = tr.final
    tr.guardrails = check(tr.final, tr.confidence, tr.branch)
    failed = [g for g in tr.guardrails if g["blocking"] and not g["passed"]]
    if failed:
        tr.blocked = True
        tr.final = SAFE
    tr.ms = int((time.time() - t0) * 1000)
    _save(tr)
    return tr

def _save(tr):
    try:
        with db() as c:
            c.execute("""INSERT INTO runs (created_at, headline, branch, answer,
                         confidence, passages, guardrails, blocked, mode, ms)
                         VALUES (?,?,?,?,?,?,?,?,?,?)""",
                      (time.strftime("%Y-%m-%d %H:%M:%S"), tr.headline, tr.branch,
                       tr.final, tr.confidence, json.dumps(tr.passages),
                       json.dumps(tr.guardrails), int(tr.blocked), tr.mode, tr.ms))
    except Exception:
        pass   # a broken database must never stop an answer


# ---------------------------------------------------------------- scoring
def score(golden):
    """golden: list of {'text':..., 'label':...}. Returns per-item and totals."""
    from sklearn.metrics import cohen_kappa_score
    rows, preds, truth = [], [], []
    for g in golden:
        tr = classify(g["text"])
        rows.append({"text": g["text"][:90], "expected": g["label"],
                     "got": tr.final, "ok": tr.final == g["label"],
                     "branch": tr.branch, "confidence": tr.confidence})
        preds.append(tr.final)
        truth.append(g["label"])
    correct = sum(r["ok"] for r in rows)
    k = cohen_kappa_score(truth, preds, labels=CATS) if len(set(truth)) > 1 else 0.0
    return {"rows": rows, "correct": correct, "total": len(rows),
            "accuracy": round(correct / len(rows), 4) if rows else 0.0,
            "kappa": round(float(k), 4)}
