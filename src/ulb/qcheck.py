"""Validate the question bank before spending money on API calls.

  * schema checks (ids unique, categories valid, gold present)
  * every gold citation is verified against Find Case Law
  * every fabricated-trap name is confirmed to have ZERO footprint on Find Case Law
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from .citations import Citation, extract, names_match
from .io import read_jsonl
from .verify import Verifier

CATEGORIES = {"citation_recall", "holding", "overruled_trap", "fabricated_trap", "jurisdiction_trap", "problem_question"}


def check(questions_path: str, results_dir: str = "results") -> None:
    qs = read_jsonl(questions_path)
    v = Verifier(cache_path=Path(results_dir) / "fcl_cache.json", reference_path=None)
    problems = 0
    confirmed: set[str] = set()
    ids = Counter(q["id"] for q in qs)
    for i, n in ids.items():
        if n > 1:
            print(f"DUPLICATE id {i}")
            problems += 1
    for q in qs:
        if q["category"] not in CATEGORIES:
            print(f"{q['id']}: bad category {q['category']}")
            problems += 1
        gold = q.get("gold", {})
        for g in gold.get("citations", []):
            for c in extract(f"{gold.get('case_name', '')} {g}"):
                res = v.verify(c)
                ok = res["verdict"] in ("VERIFIED", "VERIFIED_FOOTPRINT")
                print(f"{'ok ' if ok else 'BAD'} {q['id']}: {g}  [{res['verdict']}; FCL: {res.get('fcl_name') or '-'}; cited by {res.get('footprint')}]")
                problems += not ok
                if ok:
                    confirmed.add(c.norm)
        if q["category"] == "fabricated_trap":
            for name in gold.get("fake_names", []):
                n = v.name_exists(name)
                ok = n == 0
                print(f"{'ok ' if ok else 'BAD'} {q['id']}: fake name '{name}' footprint={n}")
                problems += not ok
            for fc in gold.get("fake_citations", []):
                for c in extract(fc):
                    if c.fcl_path:
                        res = v.lookup_path(c.fcl_path)
                        note = f"real case at that citation: {res.get('name')}" if res["status"] == "found" else "no case at that citation"
                        print(f"    {q['id']}: {fc} -> {note}")
    ref = Path(questions_path).parent / "reference_citations.jsonl"
    if ref.exists():
        from .citations import normalise
        from .io import write_jsonl
        rows = read_jsonl(ref)
        for r in rows:
            r["verified"] = r.get("verified") or normalise(r["citation"]) in confirmed
        write_jsonl(ref, rows)
        print(f"reference list: {sum(r['verified'] for r in rows)}/{len(rows)} citations confirmed")
    by = Counter(q["category"] for q in qs)
    status = Counter(q.get("status", "draft") for q in qs)
    print(f"\n{len(qs)} questions {dict(by)}  status={dict(status)}  problems={problems}")
