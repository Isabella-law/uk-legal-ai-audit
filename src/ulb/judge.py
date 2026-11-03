"""Study 2: can an AI decide real appeals it has never seen?

Design
  * Cases: real UK Supreme Court (or Court of Appeal) appeals decided AFTER each model's
    training cutoff, so the model cannot have memorised the outcome.
  * Input: a neutral, outcome-free brief you write from the judgment: facts, the issues,
    each side's submissions. Party names anonymised.
  * Output: the model writes a reasoned judgment and a machine-readable decision.
  * Scored against what the court actually did (outcome + issue-by-issue), against a
    majority-class baseline, and for calibration (Brier score).
  * Reasoning quality: blind packets for human raters, with model identities hidden.

Commands
  ulb judge run      ulb judge score      ulb judge pack      ulb judge unblind
"""
from __future__ import annotations

import csv
import json
import random
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

from . import providers
from .io import append_jsonl, load_models, read_jsonl
from .report import wilson

OUTCOMES = ["allowed", "dismissed", "allowed_in_part"]

JUDGE_SYSTEM = (
    "You are a Justice of the Supreme Court of the United Kingdom hearing an appeal. Decide it on the "
    "law of the relevant UK jurisdiction as it stood at the date of the hearing, using only the brief "
    "provided and your knowledge of the law. Write a reasoned judgment: identify the issues, state the "
    "law, apply it, and reach a conclusion on each issue. Then end your answer with a fenced ```json``` "
    "block containing exactly these keys:\n"
    '  "outcome": one of "allowed", "dismissed", "allowed_in_part" (OUTCOME of the appeal),\n'
    '  "issues": a list of {"issue": <number>, "answer": <short answer matching how the issue is framed>},\n'
    '  "confidence": your probability (0-1) that your outcome matches the actual decision,\n'
    '  "recognised_case": true if you believe you already know this real case and its result, else false,\n'
    '  "recognised_as": the case name if recognised, else null.'
)


def load_cases(cases_dir: str, include_draft: bool = False) -> list[dict]:
    cases = []
    for p in sorted(Path(cases_dir).glob("*.json")):
        if p.name.startswith("_"):
            continue  # templates
        c = json.loads(p.read_text())
        if include_draft or c.get("status") == "verified":
            cases.append(c)
    return cases


def brief(c: dict) -> str:
    parts = [f"COURT: {c.get('court', 'UKSC')}",
             f"APPEAL: {c.get('anonymised_title', 'Appellant v Respondent')}",
             f"APPEAL FROM: {c.get('appeal_from', '')}",
             "", "AGREED FACTS:", c["facts"].strip(), "", "ISSUES FOR THE COURT:"]
    parts += [f"{i}. {iss['question']}" for i, iss in enumerate(c["issues"], 1)]
    parts += ["", "APPELLANT'S SUBMISSIONS:", c["appellant_submissions"].strip(),
              "", "RESPONDENT'S SUBMISSIONS:", c["respondent_submissions"].strip()]
    if c.get("legal_materials"):
        parts += ["", "LEGISLATION / MATERIALS BEFORE THE COURT:", c["legal_materials"].strip()]
    return "\n".join(parts)


def parse_decision(text: str) -> dict | None:
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text or "", re.S)
    for b in reversed(blocks):
        try:
            d = json.loads(b)
            d["outcome"] = str(d.get("outcome", "")).strip().lower().replace(" ", "_")
            return d
        except json.JSONDecodeError:
            continue
    return None


def _after_cutoff(c: dict, m: dict) -> bool:
    cut = m.get("knowledge_cutoff")
    if not cut:
        return False  # unknown cutoff -> treat as contaminated, excluded unless forced
    return date.fromisoformat(c["decision_date"]) > date.fromisoformat(cut)


def run(cases_dir: str, models_path: str, results_dir: str = "results", only_models=None,
        include_draft=False, include_contaminated=False, repeats: int = 1, workers: int = 3) -> None:
    out = Path(results_dir) / "judge" / "raw.jsonl"
    cases = load_cases(cases_dir, include_draft)
    if not cases:
        raise SystemExit(f"No cases in {cases_dir} (status must be 'verified', or pass --include-draft).")
    done = {(r["model"], r["case_id"], r["repeat"]) for r in read_jsonl(out) if not r.get("error")}
    for m in load_models(models_path, only_models):
        eligible = [c for c in cases if include_contaminated or _after_cutoff(c, m)]
        skipped = len(cases) - len(eligible)
        todo = [(c, k) for c in eligible for k in range(repeats) if (m["name"], c["id"], k) not in done]
        print(f"[{m['name']}] {len(todo)} to run; {skipped} excluded as on/before cutoff "
              f"({m.get('knowledge_cutoff') or 'cutoff not set'})")
        if not todo:
            continue
        prov = providers.make(m)

        def task(c, k):
            res = prov.complete(JUDGE_SYSTEM, brief(c))
            return {"model": m["name"], "case_id": c["id"], "repeat": k,
                    "after_cutoff": _after_cutoff(c, m), "decision": parse_decision(res["text"]),
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **res}

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for row in ex.map(lambda ck: task(*ck), todo):
                append_jsonl(out, row)
                flag = "!" if row["error"] or not row["decision"] else " "
                print(f" {flag} {row['case_id']} -> {(row['decision'] or {}).get('outcome', row['error'] or 'unparsed')}")


def score(cases_dir: str, results_dir: str = "results", include_draft=False) -> None:
    cases = {c["id"]: c for c in load_cases(cases_dir, include_draft)}
    rows = [r for r in read_jsonl(Path(results_dir) / "judge" / "raw.jsonl") if r["case_id"] in cases and not r.get("error")]
    if not rows:
        raise SystemExit("No judge results. Run `ulb judge run`.")
    actual = Counter(c["actual_outcome"] for c in cases.values())
    base_k = actual.most_common(1)[0][1]
    stats = defaultdict(lambda: {"n": 0, "correct": 0, "iss_k": 0, "iss_n": 0, "brier": 0.0, "brier_n": 0,
                                 "unparsed": 0, "recognised": 0, "contaminated": 0})
    for r in rows:
        s, c, d = stats[r["model"]], cases[r["case_id"]], r["decision"]
        s["n"] += 1
        s["contaminated"] += not r.get("after_cutoff", False)
        if not d:
            s["unparsed"] += 1
            continue
        ok = d["outcome"] == c["actual_outcome"]
        s["correct"] += ok
        s["recognised"] += bool(d.get("recognised_case"))
        conf = d.get("confidence")
        if isinstance(conf, (int, float)) and 0 <= conf <= 1:
            s["brier"] += (conf - ok) ** 2
            s["brier_n"] += 1
        answers = {int(i["issue"]): str(i.get("answer", "")) for i in d.get("issues", []) if str(i.get("issue", "")).isdigit()}
        for i, iss in enumerate(c["issues"], 1):
            if "actual_answer" in iss and i in answers:
                s["iss_n"] += 1
                s["iss_k"] += _answer_match(answers[i], iss)
    out_md = ["# AI Judge study: results", "",
              f"Cases: {len(cases)} · actual outcomes: {dict(actual)} · majority-class baseline: "
              f"{base_k/len(cases)*100:.1f}%", "",
              "| Model | Outcome accuracy (95% CI) | Issue accuracy | Brier ↓ | Unparsed | Claimed to recognise | Run on/before cutoff |",
              "|---|---|---|---|---|---|---|"]
    for m, s in sorted(stats.items()):
        p, lo, hi = wilson(s["correct"], s["n"])
        ip = f"{s['iss_k']}/{s['iss_n']}" if s["iss_n"] else "—"
        br = f"{s['brier']/s['brier_n']:.3f}" if s["brier_n"] else "—"
        out_md.append(f"| {m} | {p*100:.1f}% ({lo*100:.0f}–{hi*100:.0f}) n={s['n']} | {ip} | {br} | "
                      f"{s['unparsed']} | {s['recognised']} | {s['contaminated']} |")
    md = "\n".join(out_md) + "\n"
    (Path(results_dir) / "judge" / "report.md").write_text(md)
    print(md)


def _answer_match(model_answer: str, iss: dict) -> bool:
    a = model_answer.strip().lower()
    accepted = [x.lower() for x in iss.get("accepted_answers", [iss["actual_answer"]])]
    return any(a.startswith(x) or x in a.split() for x in accepted)


def pack(cases_dir: str, results_dir: str = "results", include_draft=False, seed: int = 7) -> None:
    """Blind packets for human rating of reasoning quality."""
    cases = {c["id"]: c for c in load_cases(cases_dir, include_draft)}
    rows = [r for r in read_jsonl(Path(results_dir) / "judge" / "raw.jsonl")
            if r["case_id"] in cases and not r.get("error") and r["repeat"] == 0]
    outdir = Path(results_dir) / "judge" / "blind"
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    key, sheet = {}, []
    by_case = defaultdict(list)
    for r in rows:
        by_case[r["case_id"]].append(r)
    for cid, rs in sorted(by_case.items()):
        rng.shuffle(rs)
        md = [f"# Case {cid}: blind judgments", "", "## Brief", "", brief(cases[cid]), ""]
        for j, r in enumerate(rs, 1):
            label = f"{cid}-J{j}"
            key[label] = r["model"]
            body = re.sub(r"```json.*?```", "", r["text"], flags=re.S).strip()
            md += [f"---\n\n## Judgment {label}", "", body, ""]
            sheet.append({"judgment": label, "issues_identified_1to5": "", "law_correct_1to5": "",
                          "application_1to5": "", "coherence_1to5": "", "would_pass_as_human_y_n": "", "notes": ""})
        (outdir / f"{cid}.md").write_text("\n".join(md))
    with (outdir / "ratings.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sheet[0]))
        w.writeheader()
        w.writerows(sheet)
    (Path(results_dir) / "judge" / "KEY_do_not_open.json").write_text(json.dumps(key, indent=1))
    print(f"Wrote {len(by_case)} packets + ratings.csv to {outdir}. The key is stored separately; give "
          "raters only the blind/ folder.")


def unblind(ratings_csv: str, results_dir: str = "results") -> None:
    key = json.loads((Path(results_dir) / "judge" / "KEY_do_not_open.json").read_text())
    dims = ["issues_identified_1to5", "law_correct_1to5", "application_1to5", "coherence_1to5"]
    agg = defaultdict(lambda: defaultdict(list))
    human = defaultdict(lambda: [0, 0])
    with open(ratings_csv) as f:
        for row in csv.DictReader(f):
            m = key.get(row["judgment"])
            if not m:
                continue
            for d in dims:
                if row[d].strip():
                    agg[m][d].append(float(row[d]))
            if row["would_pass_as_human_y_n"].strip():
                human[m][0] += row["would_pass_as_human_y_n"].strip().lower().startswith("y")
                human[m][1] += 1
    md = ["| Model | " + " | ".join(d.replace("_1to5", "") for d in dims) + " | Passes as human |",
          "|---|" + "---|" * (len(dims) + 1)]
    for m in sorted(agg):
        cells = [f"{sum(v)/len(v):.2f} (n={len(v)})" if (v := agg[m][d]) else "—" for d in dims]
        k, n = human[m]
        md.append(f"| {m} | " + " | ".join(cells) + f" | {k}/{n} |")
    out = "\n".join(md) + "\n"
    (Path(results_dir) / "judge" / "ratings_report.md").write_text(out)
    print(out)
