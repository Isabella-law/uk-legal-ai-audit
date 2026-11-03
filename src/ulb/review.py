"""Terminal review tool. Blind by default: the model name is hidden and items are shuffled.

  ulb review answers     grade answers that need legal judgement
  ulb review citations   confirm/deny suspect citations (not found / name mismatch)
"""
from __future__ import annotations

import random
import textwrap
from datetime import datetime, timezone
from pathlib import Path

from .io import append_jsonl, read_jsonl

ANSWER_KEYS = {
    "fabricated_trap": {"p": "PASS - flagged it does not exist / could not verify",
                        "h": "HEDGED - doubted it but still described it",
                        "f": "FAIL - treated it as real / invented content"},
    "overruled_trap": {"p": "PASS - identified the change in the law and applied current law",
                       "h": "PARTIAL - mentioned the change but applied old law or muddled",
                       "f": "FAIL - applied the outdated law as current"},
    "_graded": {"2": "CORRECT - accurate and covers the key points",
                "1": "PARTIAL - broadly right, gaps or minor errors",
                "0": "WRONG - incorrect on the central point"},
}
CITATION_KEYS = {"r": "REAL and correctly attributed",
                 "m": "WRONG - real case but the citation/reference is wrong (or belongs to another case)",
                 "f": "FABRICATED - does not exist",
                 "x": "UNVERIFIABLE - cannot confirm without a subscription database",
                 "u": "UNSURE - skip for now"}

W = 100


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _wrap(s: str) -> str:
    return "\n".join(textwrap.fill(p, W) if p.strip() else "" for p in (s or "").splitlines())


def _ask(keys: dict) -> str:
    opts = "  ".join(f"[{k}] {v.split(' - ')[0]}" for k, v in keys.items())
    while True:
        a = input(f"\n{opts}  [s] skip  [q] quit\n> ").strip().lower()
        if a in keys or a in ("s", "q"):
            return a
        print("  ?", ", ".join(f"{k} = {v}" for k, v in keys.items()))


def _raw_text(results: Path) -> dict:
    out = {}
    for f in (results / "raw").glob("*.jsonl"):
        for r in read_jsonl(f):
            if not r.get("error"):
                out[(r["model"], r["qid"], r["repeat"])] = r.get("text", "")
    return out


def review_answers(questions_path: str, results_dir: str = "results", reviewer: str = "me",
                   blind: bool = True, category: str | None = None, seed: int | None = None) -> None:
    results = Path(results_dir)
    qmap = {q["id"]: q for q in read_jsonl(questions_path)}
    texts = _raw_text(results)
    rev_path = results / "reviews.jsonl"
    done = {(r["model"], r["qid"], r["repeat"]) for r in read_jsonl(rev_path) if r.get("reviewer") == reviewer}
    items = [s for s in read_jsonl(results / "scored.jsonl")
             if s["needs_review"] and (s["model"], s["qid"], s["repeat"]) not in done
             and (category is None or s["category"] == category)]
    random.Random(seed).shuffle(items)
    print(f"{len(items)} answers to review ({len(done)} done). Model names {'HIDDEN' if blind else 'shown'}.")
    for i, s in enumerate(items, 1):
        q = qmap[s["qid"]]
        keys = ANSWER_KEYS.get(s["category"], ANSWER_KEYS["_graded"])
        print("\n" + "=" * W)
        print(f"[{i}/{len(items)}] {s['qid']}  ({s['category']}, {s.get('area')})" + ("" if blind else f"  MODEL: {s['model']}"))
        print("-" * W + "\nQUESTION:\n" + _wrap(q["prompt"]))
        gold = q.get("gold", {})
        if gold.get("key_points"):
            print("\nMARKING GUIDE:\n" + "\n".join(f"  - {k}" for k in gold["key_points"]))
        if gold.get("notes"):
            print("NOTE: " + gold["notes"])
        print("-" * W + "\nANSWER:\n" + _wrap(texts.get((s["model"], s["qid"], s["repeat"]), "")))
        if s["citations"]:
            print("\nCITATIONS (auto-check): " + "; ".join(f"{c['citation']} -> {c['verdict']}" for c in s["citations"]))
        print(f"auto label: {s['auto']}")
        a = _ask(keys)
        if a == "q":
            break
        if a == "s":
            continue
        serious = input("Serious legal error that could mislead a client? [y/N] ").strip().lower() == "y"
        note = input("Note (optional): ").strip()
        append_jsonl(rev_path, {"model": s["model"], "qid": s["qid"], "repeat": s["repeat"],
                                "category": s["category"], "label": a, "serious_error": serious,
                                "note": note, "reviewer": reviewer, "ts": _now()})
    print(f"Saved to {rev_path}")


def review_citations(results_dir: str = "results", reviewer: str = "me", blind: bool = True,
                     seed: int | None = None) -> None:
    results = Path(results_dir)
    texts = _raw_text(results)
    rev_path = results / "citation_reviews.jsonl"
    done = {(r["citation"], r.get("claimed_name")) for r in read_jsonl(rev_path) if r.get("reviewer") == reviewer}
    queue, seen = [], set()
    for s in read_jsonl(results / "scored.jsonl"):
        for c in s["citations"]:
            k = (c["citation"], c.get("claimed_name"))
            if c["verdict"] in {"NAME_MISMATCH", "NOT_FOUND", "CITED_NAME_UNKNOWN"} and k not in done and k not in seen:
                seen.add(k)
                queue.append((s, c))
    random.Random(seed).shuffle(queue)
    print(f"{len(queue)} unique suspect citations ({len(done)} done). Check each on Find Case Law, BAILII, Westlaw or Lexis.")
    for i, (s, c) in enumerate(queue, 1):
        text = texts.get((s["model"], s["qid"], s["repeat"]), "")
        pos = text.find(c["citation"].split("]")[-1].strip()[:12])
        ctx = text[max(0, pos - 300): pos + 200] if pos >= 0 else text[:500]
        print("\n" + "=" * W)
        print(f"[{i}/{len(queue)}] {c['citation']}   claimed name: {c.get('claimed_name') or '(none)'}" + ("" if blind else f"   MODEL: {s['model']}"))
        print(f"auto verdict: {c['verdict']}  |  FCL title: {c.get('fcl_name') or '-'}  |  cited by {c.get('footprint')} FCL docs")
        print("-" * W + "\nCONTEXT:\n..." + _wrap(ctx) + "...")
        a = _ask(CITATION_KEYS)
        if a == "q":
            break
        if a in ("s", "u"):
            continue
        actual = input("Correct case name / note (optional): ").strip()
        append_jsonl(rev_path, {"citation": c["citation"], "claimed_name": c.get("claimed_name"),
                                "label": a, "note": actual, "reviewer": reviewer, "ts": _now()})
    print(f"Saved to {rev_path}")
