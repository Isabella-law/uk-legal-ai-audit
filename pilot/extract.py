"""Extract pilot answers verbatim from sub-agent transcripts -> results/raw/<model>.jsonl"""
import json, re, sys
from pathlib import Path
T = Path(sys.argv[1])
RUNS = {  # task id -> (model label, batch)
 "ac32f88885951a1af": ("claude-haiku", 1), "a8881d19036c6f184": ("claude-sonnet", 1), "a0274816f0390c7b4": ("claude-opus", 1),
 "aac44c84168627c90": ("claude-haiku", 2), "afd5c39708b04e1a8": ("claude-sonnet", 2), "aaff3611c0ecbf272": ("claude-opus", 2),
 "a30275ba11e078cab": ("claude-haiku", 3), "a1058399b0d2ac61b": ("claude-sonnet", 3), "a0ff4f5031b2f9784": ("claude-opus", 3),
}
key = json.load(open("pilot/id_key.json"))
log = []
for tid, (label, b) in RUNS.items():
    f = T / f"{tid}.output"
    if not f.exists():
        log.append({"task": tid, "model": label, "batch": b, "status": "missing"}); continue
    text, served, tools = None, set(), []
    for l in f.open():
        try: d = json.loads(l)
        except: continue
        m = d.get("message") or {}
        if m.get("role") != "assistant": continue
        if m.get("model"): served.add(m["model"])
        for blk in m.get("content") or []:
            if blk.get("type") == "tool_use":
                tools.append(blk.get("name"))
                if blk.get("name") == "SubagentHandback":
                    inp = blk.get("input") or {}
                    cand = next((v for v in inp.values() if isinstance(v, str) and "=== Q" in v), None)
                    if cand: text = cand
            elif blk.get("type") == "text" and "=== Q" in (blk.get("text") or ""):
                text = blk["text"]
    if not text:
        log.append({"task": tid, "model": label, "batch": b, "status": "no_answers", "served": sorted(served)}); continue
    parts = re.split(r"^===\s*(Q\d{3})\s*$", text, flags=re.M)
    answers = {parts[i]: parts[i+1].strip() for i in range(1, len(parts)-1, 2)}
    out = Path("results/raw") / f"{label}.jsonl"; out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as fo:
        for n, a in answers.items():
            fo.write(json.dumps({"qid": key[n], "pilot_qnum": n, "model": label, "model_id": ",".join(sorted(served)),
                     "repeat": 0, "system_hash": "pilot-batched", "batch": b, "ts": "2026-11-03", "text": a,
                     "stop_reason": "end_turn", "model_served": ",".join(sorted(served)), "usage": {}, "latency_s": None, "error": None},
                     ensure_ascii=False) + "\n")
    forbidden = [t for t in tools if t != "SubagentHandback"]
    log.append({"task": tid, "model": label, "batch": b, "status": "ok", "answers": len(answers),
                "served": sorted(served), "tools_used": tools, "forbidden_tool_use": bool(forbidden)})
json.dump(log, open("pilot/run_log.json", "w"), indent=1)
for r in log: print(r)
