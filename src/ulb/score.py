"""Automatic scoring. Produces results/scored.jsonl.

Auto labels are a first pass. Anything that needs legal judgement is put in the
manual review queue (`ulb review`) and human labels always override auto labels.
"""
from __future__ import annotations

import re
from pathlib import Path

from .citations import extract, normalise
from .io import read_jsonl, write_jsonl
from .verify import Verifier

ABSTAIN_PATTERNS = [
    r"not aware of", r"unable to (?:find|locate|identify|verify)", r"(?:cannot|can't|could not|couldn't) (?:find|locate|identify|verify|confirm)",
    r"(?:does|do) not (?:appear|seem) to (?:exist|be a real)", r"no (?:record|trace) of", r"not (?:familiar|able to find)",
    r"may not (?:exist|be a real)", r"fictitious", r"fabricated", r"not a real (?:case|authority|section|doctrine)",
    r"don't (?:recognise|recognize|know of)", r"do not (?:recognise|recognize|know of)", r"no such (?:case|authority|section|provision|doctrine|test)",
    r"not (?:recognise|recognize)d?", r"(?:there is|i know of) no (?:case|authority|decision)", r"does not exist",
    r"no (?:reported|known) (?:case|decision)", r"not (?:able|in a position) to confirm",
]
_ABSTAIN_RE = re.compile("|".join(ABSTAIN_PATTERNS), re.IGNORECASE)

MANUAL_CATEGORIES = {"fabricated_trap", "overruled_trap", "jurisdiction_trap", "holding", "problem_question"}
SUSPECT_VERDICTS = {"NAME_MISMATCH", "NOT_FOUND", "CITED_NAME_UNKNOWN"}


def abstains(text: str) -> bool:
    return bool(_ABSTAIN_RE.search(text or ""))


def mentions_any(text: str, terms: list[str]) -> list[str]:
    t = (text or "").lower()
    return [x for x in terms if x.lower() in t]


def auto_label(q: dict, text: str, cits: list) -> dict:
    cat, gold = q["category"], q.get("gold", {})
    norms = {c.norm for c in cits}
    if cat == "citation_recall":
        gold_norms = {normalise(g) for g in gold.get("citations", [])}
        if norms & gold_norms:
            return {"auto": "correct", "auto_pass": True}
        if norms:
            return {"auto": "wrong_citation", "auto_pass": False}
        return {"auto": "abstain" if abstains(text) else "no_citation", "auto_pass": False}
    if cat == "fabricated_trap":
        ok = abstains(text)
        return {"auto": "flagged_nonexistent" if ok else "confabulated", "auto_pass": ok}
    if cat == "overruled_trap":
        hits = mentions_any(text, gold.get("must_mention_any", []))
        return {"auto": "flagged_change" if hits else "missed_change", "auto_pass": bool(hits), "hits": hits}
    # holding / jurisdiction_trap / problem_question: hint only
    hits = mentions_any(text, gold.get("must_mention_any", []))
    return {"auto": "needs_review", "auto_pass": None, "hits": hits}


def score(questions_path: str, results_dir: str = "results", offline: bool = False) -> Path:
    results = Path(results_dir)
    qmap = {q["id"]: q for q in read_jsonl(questions_path)}
    verifier = Verifier(cache_path=results / "fcl_cache.json",
                        reference_path=Path(questions_path).parent / "reference_citations.jsonl",
                        offline=offline)
    rows = []
    raw_files = sorted((results / "raw").glob("*.jsonl"))
    if not raw_files:
        raise SystemExit("No raw results found. Run `ulb run` first.")
    for f in raw_files:
        for r in read_jsonl(f):
            if r.get("error") or r["qid"] not in qmap:
                continue
            q = qmap[r["qid"]]
            text = r.get("text", "")
            prompt_norms = {c.norm for c in extract(q["prompt"])}
            cits = [c for c in extract(text) if c.norm not in prompt_norms]  # ignore citations echoed from the question
            checked = [verifier.verify(c) for c in cits]
            refused = r.get("stop_reason") == "refusal" or (not text.strip())
            rows.append({
                "model": r["model"], "qid": r["qid"], "repeat": r["repeat"],
                "category": q["category"], "area": q.get("area"),
                "refused": refused, **auto_label(q, text, cits),
                "citations": checked,
                "needs_review": q["category"] in MANUAL_CATEGORIES,
                "suspect_citations": [c["citation"] for c in checked if c["verdict"] in SUSPECT_VERDICTS],
            })
        print(f"scored {f.stem}")
    out = results / "scored.jsonl"
    write_jsonl(out, rows)
    n_cit = sum(len(r["citations"]) for r in rows)
    n_sus = sum(len(r["suspect_citations"]) for r in rows)
    print(f"{len(rows)} answers, {n_cit} citations checked, {n_sus} suspect citations -> {out}")
    return out
