"""Collect all real results into one JSON blob for the showcase site."""
import json, csv
from pathlib import Path
R = Path("results")
q = [json.loads(l) for l in open("data/questions.jsonl")]
raw = {}
for f in (R/"raw").glob("*.jsonl"):
    for l in f.open():
        r = json.loads(l); raw[(r["model"], r["qid"])] = r["text"]
scored = {(s["model"], s["qid"]): s for s in map(json.loads, open(R/"scored.jsonl"))}
rev = {(r["model"], r["qid"]): r for r in map(json.loads, open(R/"reviews.jsonl"))}
crev = {(r["citation"], r["claimed_name"]): r for r in map(json.loads, open(R/"citation_reviews.jsonl"))}
AUTO = {"VERIFIED":"real","VERIFIED_FOOTPRINT":"real","NAME_MISMATCH":"wrong","NOT_FOUND":"fabricated","CITED_NAME_UNKNOWN":"unknown"}
MAN = {"r":"real","m":"wrong","f":"fabricated","x":"unverifiable"}
models = ["claude-haiku","claude-sonnet","claude-opus"]
questions = []
for x in q:
    ans = {}
    for m in models:
        s = scored[(m, x["id"])]; rv = rev.get((m, x["id"]))
        cits = []
        for c in s["citations"]:
            cr = crev.get((c["citation"], c.get("claimed_name")))
            cits.append({"c": c["citation"], "n": c.get("claimed_name"), "v": c["verdict"],
                         "s": MAN[cr["label"]] if cr else AUTO[c["verdict"]], "e": cr["note"] if cr else c.get("method")})
        grade = rv["label"] if rv else ("2" if s["auto_pass"] else "0")
        ans[m] = {"t": raw[(m, x["id"])], "g": grade, "auto": s["auto"], "note": (rv or {}).get("note", ""),
                  "serious": (rv or {}).get("serious_error", False), "cits": cits}
    questions.append({"id": x["id"], "cat": x["category"], "area": x.get("area"), "p": x["prompt"],
                      "kp": x["gold"].get("key_points", []), "gold_cits": x["gold"].get("citations", []), "ans": ans})
summary = list(csv.DictReader(open(R/"summary.csv")))
cases = []
jr = [json.loads(l) for l in open(R/"judge/raw.jsonl")]
for p in sorted(Path("data/judge_cases").glob("J-*.json")):
    c = json.loads(p.read_text())
    preds = {r["model"]: {"o": r["decision"]["outcome"], "conf": r["decision"]["confidence"],
             "rec": r["decision"].get("recognised_as") if r["decision"].get("recognised_case") else None,
             "iss": [i["answer"] for i in r["decision"]["issues"]], "t": r["text"].split("```json")[0].strip()}
             for r in jr if r["case_id"] == c["id"]}
    cases.append({"id": c["id"], "title": c["real_title"], "cit": c["neutral_citation"], "date": c["decision_date"],
                  "actual": c["actual_outcome"], "maj": c["majority"], "url": c["source_url"], "anon": c["anonymised_title"],
                  "issues": [i["question"] for i in c["issues"]], "actual_iss": [i["actual_answer"] for i in c["issues"]],
                  "summary": c["actual_reasoning_summary"], "evidence": c["outcome_evidence"], "preds": preds})
log = json.load(open("pilot/run_log.json")); jlog = json.load(open("pilot/judge_run_log.json"))
out = {"questions": questions, "summary": summary, "cases": sorted(cases, key=lambda c: c["date"]),
       "runs": [{"model": r["model"], "batch": r["batch"], "served": r["served"], "forbidden": r["forbidden_tool_use"], "n": r["answers"]} for r in log],
       "judge_runs": [{"model": r["model"], "set": r["set"], "served": r["served"], "calls": [c[0] for c in r["calls"]], "forbidden": bool(r["forbidden"])} for r in jlog]}
Path("site/data.json").write_text(json.dumps(out, ensure_ascii=False))
print(len(json.dumps(out))//1024, "KB")
