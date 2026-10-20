"""The web interface. Option A never needs to read this file either."""
import os, json, pathlib
import pandas as pd
import gradio as gr

from . import engine, config

HERE = pathlib.Path(__file__).parent
engine.init_db()

def _golden():
    p = HERE.parent / "week1_data.csv"
    if not p.exists():
        return []
    df = pd.read_csv(p)
    m = df[df["set"] == "main"]
    return [{"text": r.text, "label": r.official_label} for r in m.itertuples()]


# ------------------------------------------------------------ page 1
def do_classify(headline):
    tr = engine.classify(headline)
    verdict = f"## {tr.final}\n\nConfidence {tr.confidence:.2f}"
    if tr.blocked:
        verdict = f"## Blocked\n\n{tr.final}"
    trace = [
        f"**Branch**  `{tr.branch}` because {tr.why_branch}",
        f"**Mode**  {tr.mode}" + ("  (no API key, using the stand-in)" if tr.mode == "demo" else ""),
        f"**Time**  {tr.ms} ms",
        "",
        "**Passages retrieved**",
    ]
    if tr.passages:
        for p in tr.passages:
            trace.append(f"- `{p['file']}` / {p['heading']}  (score {p['score']})")
    else:
        trace.append("- none scored above the threshold")
    trace += ["", "**Guardrails**"]
    for g in tr.guardrails:
        trace.append(f"- {'PASS' if g['passed'] else 'FAIL'}  {g['name']} — {g['detail']}")
    return verdict, "\n".join(trace)


# ------------------------------------------------------------ page 2
def do_score(progress=gr.Progress()):
    golden = _golden()
    if not golden:
        return "week1_data.csv was not found next to the app.", None
    s = engine.score(golden)
    head = (f"## {s['correct']} / {s['total']} correct\n\n"
            f"Accuracy **{s['accuracy']*100:.1f}%**  ·  Cohen's kappa **{s['kappa']}**\n\n"
            f"Mode: {'live model' if engine.live_mode() else 'demo stand-in, the prompt is ignored'}")
    df = pd.DataFrame(s["rows"])[["text", "expected", "got", "ok", "confidence"]]
    return head, df


# ------------------------------------------------------------ page 3
def do_runs():
    with engine.db() as c:
        rows = c.execute("""SELECT created_at, headline, branch, answer,
                            confidence, blocked, mode, ms
                            FROM runs ORDER BY id DESC LIMIT 50""").fetchall()
    if not rows:
        return pd.DataFrame([{"nothing yet": "classify something first"}])
    return pd.DataFrame([dict(r) for r in rows])


# ------------------------------------------------------------ page 4
def do_health():
    files = [f for f in config.KNOWLEDGE_FILES
             if (HERE / "knowledge" / f).exists()]
    missing = [f for f in config.KNOWLEDGE_FILES if f not in files]
    with engine.db() as c:
        n = c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    lines = [
        "## What is switched on",
        "",
        f"- **Model key**  {'present, using the real model' if engine.live_mode() else 'NOT SET, using the demo stand-in'}",
        f"- **Model**  `{config.MODEL}`",
        f"- **Database**  working, {n} rows stored",
        f"- **Knowledge files loaded**  {files if files else 'none'}",
    ]
    if missing:
        lines.append(f"- **Listed but not found**  {missing}  ← check the file name in config.py")
    lines += [
        f"- **Passages shown to the model**  {config.KNOWLEDGE_PASSAGES}",
        f"- **Relevance threshold**  {config.KNOWLEDGE_THRESHOLD}",
        f"- **Confidence floor**  {config.CONFIDENCE_FLOOR}",
        f"- **Routing rules**  {len(config.ROUTING_RULES)}",
        f"- **Banned phrases**  {len(config.BANNED_PHRASES)}",
        "",
        "If something here is not what you expected, the problem is in `app/config.py`.",
    ]
    return "\n".join(lines)


def build():
    with gr.Blocks(title="Newsroom Triage") as demo:
        gr.Markdown("# Newsroom Triage\nPaste a news headline. It tells you which "
                    "of four categories it belongs to, and shows you exactly how it decided.")
        with gr.Tab("Classify"):
            inp = gr.Textbox(label="News headline", lines=3,
                             placeholder="Paste a headline here")
            btn = gr.Button("Classify", variant="primary")
            out = gr.Markdown()
            tr = gr.Markdown()
            btn.click(do_classify, inp, [out, tr])
        with gr.Tab("Scoring"):
            gr.Markdown("Runs your thirty labelled items from Week 1 and scores itself.")
            sbtn = gr.Button("Run the scoring", variant="primary")
            shead = gr.Markdown()
            stab = gr.Dataframe(wrap=True)
            sbtn.click(do_score, None, [shead, stab])
        with gr.Tab("Runs"):
            gr.Markdown("Every question this app has been asked.")
            rbtn = gr.Button("Refresh")
            rtab = gr.Dataframe(wrap=True)
            rbtn.click(do_runs, None, rtab)
        with gr.Tab("Health"):
            hbtn = gr.Button("Check")
            hout = gr.Markdown()
            hbtn.click(do_health, None, hout)
    return demo
