"""Aggregate scored + reviewed results into paper-ready tables.

Outputs (in results/):
  summary.csv        one row per model, every metric with 95% Wilson intervals
  report.md          markdown tables to paste into the paper
  report.html        self-contained dashboard (no internet needed)
  citations.csv      every citation with its final status (audit trail)
"""
from __future__ import annotations

import csv
import html
import math
from collections import defaultdict
from pathlib import Path

from .io import read_jsonl


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return (float("nan"),) * 3
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


AUTO_CIT_STATUS = {"VERIFIED": "real", "VERIFIED_FOOTPRINT": "real", "NAME_MISMATCH": "misattributed",
                   "NOT_FOUND": "fabricated", "CITED_NAME_UNKNOWN": "unknown", "ERROR": "unknown"}
MANUAL_CIT_STATUS = {"r": "real", "m": "misattributed", "f": "fabricated", "x": "unknown"}

METRICS = [
    # key, label, higher_is_better
    ("citation_recall", "Citation recall accuracy", True),
    ("fabricated_trap", "Fake-case trap: correctly flagged", True),
    ("overruled_trap", "Overruled-law trap: caught", True),
    ("quality", "Answer quality (holding / jurisdiction / problem)", True),
    ("serious_error", "Answers with serious legal error", False),
    ("cit_fabricated", "Citations fabricated", False),
    ("cit_misattributed", "Citations wrong (real case, wrong reference)", False),
    ("cit_unknown", "Citations unverifiable", False),
    ("cit_real", "Citations verified real", True),
]


def build(questions_path: str, results_dir: str = "results", reviewer: str | None = None) -> dict:
    results = Path(results_dir)
    scored = read_jsonl(results / "scored.jsonl")
    if not scored:
        raise SystemExit("Nothing scored yet. Run `ulb score`.")
    reviews = {}
    for r in read_jsonl(results / "reviews.jsonl"):
        if reviewer is None or r["reviewer"] == reviewer:
            reviews[(r["model"], r["qid"], r["repeat"])] = r  # last label wins
    cit_reviews = {}
    for r in read_jsonl(results / "citation_reviews.jsonl"):
        if reviewer is None or r["reviewer"] == reviewer:
            cit_reviews[(r["citation"], r.get("claimed_name"))] = r["label"]

    agg = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # model -> metric -> [k, n]
    meta = defaultdict(lambda: {"answers": 0, "refused": 0, "reviewed": 0, "needs_review": 0,
                                "cit_total": 0, "cit_confirmed": 0})
    cit_rows = []
    agree = [0, 0]  # auto vs human agreement on pass/fail categories

    for s in scored:
        m, key = s["model"], (s["model"], s["qid"], s["repeat"])
        meta[m]["answers"] += 1
        meta[m]["refused"] += s["refused"]
        rv = reviews.get(key)
        if s["needs_review"]:
            meta[m]["needs_review"] += 1
            meta[m]["reviewed"] += rv is not None
        cat = s["category"]

        if cat == "citation_recall":
            agg[m]["citation_recall"][0] += bool(s["auto_pass"])
            agg[m]["citation_recall"][1] += 1
        elif cat in ("fabricated_trap", "overruled_trap"):
            if rv:
                passed = rv["label"] == "p"
                if s["auto_pass"] is not None:
                    agree[0] += (s["auto_pass"] == passed)
                    agree[1] += 1
            else:
                passed = bool(s["auto_pass"])
            agg[m][cat][0] += passed
            agg[m][cat][1] += 1
        elif rv:  # graded categories count only once reviewed
            agg[m]["quality"][0] += int(rv["label"])
            agg[m]["quality"][1] += 2
        if rv:
            agg[m]["serious_error"][0] += bool(rv.get("serious_error"))
            agg[m]["serious_error"][1] += 1

        for c in s["citations"]:
            manual = cit_reviews.get((c["citation"], c.get("claimed_name")))
            status = MANUAL_CIT_STATUS.get(manual) or AUTO_CIT_STATUS[c["verdict"]]
            confirmed = manual is not None or c["verdict"] in ("VERIFIED", "VERIFIED_FOOTPRINT")
            meta[m]["cit_total"] += 1
            meta[m]["cit_confirmed"] += confirmed
            for st in ("real", "fabricated", "misattributed", "unknown"):
                agg[m][f"cit_{st}"][0] += status == st
                agg[m][f"cit_{st}"][1] += 1
            cit_rows.append({"model": m, "qid": s["qid"], "repeat": s["repeat"], "citation": c["citation"],
                             "claimed_name": c.get("claimed_name") or "", "fcl_name": c.get("fcl_name") or "",
                             "auto_verdict": c["verdict"], "manual": manual or "", "final_status": status,
                             "confirmed": confirmed})

    models = sorted(meta)
    table = {}
    for m in models:
        row = {}
        for key, _, _ in METRICS:
            k, n = agg[m][key]
            row[key] = (k, n, *wilson(k, n))
        table[m] = row

    _write_csv(results / "summary.csv", models, table, meta)
    with (results / "citations.csv").open("w", newline="") as f:
        if cit_rows:
            w = csv.DictWriter(f, fieldnames=list(cit_rows[0]))
            w.writeheader()
            w.writerows(cit_rows)
    md = _markdown(models, table, meta, agree)
    (results / "report.md").write_text(md)
    (results / "report.html").write_text(_html(models, table, meta, agree))
    print(md)
    print(f"\nWrote {results/'summary.csv'}, {results/'report.md'}, {results/'report.html'}, {results/'citations.csv'}")
    return table


def _fmt(cell) -> str:
    k, n, p, lo, hi = cell
    if n == 0:
        return "—"
    return f"{p*100:.1f}% ({lo*100:.0f}–{hi*100:.0f}) n={n}"


def _write_csv(path, models, table, meta):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        hdr = ["model", "answers", "refused", "reviewed", "needs_review", "citations", "citations_confirmed"]
        for key, _, _ in METRICS:
            hdr += [f"{key}_k", f"{key}_n", f"{key}_p", f"{key}_lo", f"{key}_hi"]
        w.writerow(hdr)
        for m in models:
            mm = meta[m]
            row = [m, mm["answers"], mm["refused"], mm["reviewed"], mm["needs_review"], mm["cit_total"], mm["cit_confirmed"]]
            for key, _, _ in METRICS:
                k, n, p, lo, hi = table[m][key]
                row += [k, n, f"{p:.4f}", f"{lo:.4f}", f"{hi:.4f}"]
            w.writerow(row)


def _status_lines(models, meta, agree):
    lines = []
    for m in models:
        mm = meta[m]
        lines.append(f"- **{m}**: {mm['answers']} answers, {mm['refused']} refused/empty; "
                     f"{mm['reviewed']}/{mm['needs_review']} manually reviewed; "
                     f"{mm['cit_confirmed']}/{mm['cit_total']} citations confirmed.")
    if agree[1]:
        lines.append(f"- Auto-label vs human agreement on trap questions: {agree[0]}/{agree[1]} "
                     f"({agree[0]/agree[1]*100:.1f}%).")
    return lines


def _markdown(models, table, meta, agree) -> str:
    out = ["# UK Legal AI Hallucination Audit: results", "",
           "Values are proportions with 95% Wilson confidence intervals. Unreviewed items use automatic labels "
           "and are **provisional** until manual review is complete.", "", "## Status", ""]
    out += _status_lines(models, meta, agree)
    out += ["", "## Metrics", "", "| Metric | " + " | ".join(models) + " |",
            "|---|" + "---|" * len(models)]
    for key, label, hib in METRICS:
        arrow = "↑" if hib else "↓"
        out.append(f"| {label} {arrow} | " + " | ".join(_fmt(table[m][key]) for m in models) + " |")
    return "\n".join(out) + "\n"


def _html(models, table, meta, agree) -> str:
    def bar(cell, hib):
        k, n, p, lo, hi = cell
        if n == 0:
            return '<td class="na">—</td>'
        cls = "good" if (p >= 0.8 if hib else p <= 0.05) else "bad" if (p < 0.5 if hib else p > 0.15) else "mid"
        return (f'<td><div class="cell"><div class="track"><div class="fill {cls}" style="width:{p*100:.1f}%"></div>'
                f'<div class="ci" style="left:{lo*100:.1f}%;width:{(hi-lo)*100:.1f}%"></div></div>'
                f'<span>{p*100:.1f}%</span><small>{lo*100:.0f}–{hi*100:.0f}% · n={n}</small></div></td>')
    rows = "".join(f"<tr><th>{html.escape(label)} <em>{'higher better' if hib else 'lower better'}</em></th>"
                   + "".join(bar(table[m][key], hib) for m in models) + "</tr>" for key, label, hib in METRICS)
    status = "".join(f"<li>{html.escape(l.lstrip('- ').replace('**', ''))}</li>" for l in _status_lines(models, meta, agree))
    heads = "".join(f"<th>{html.escape(m)}</th>" for m in models)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>UK Legal AI Audit</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1d1b;--mute:#6b6a65;--line:#e4e1d8;--track:#ece9e1;--good:#2f7d5b;--mid:#c08a2b;--bad:#b3412f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151513;--fg:#ecebe6;--mute:#9b9a93;--line:#2c2b28;--track:#2a2926}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 Georgia,'Times New Roman',serif;margin:0;padding:32px 16px}}
main{{max-width:1100px;margin:auto}} h1{{font-weight:normal;font-size:28px;margin:0 0 4px}}
p.sub{{color:var(--mute);margin:0 0 24px;font-family:system-ui,sans-serif;font-size:13px}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-family:system-ui,sans-serif;font-size:13px}}
th,td{{border-bottom:1px solid var(--line);padding:10px 8px;text-align:left;vertical-align:middle}}
thead th{{font-weight:600}} tbody th{{font-weight:500;width:26%}} tbody th em{{display:block;color:var(--mute);font-style:normal;font-size:11px;font-weight:normal}}
.cell{{display:grid;grid-template-columns:1fr auto;gap:2px 8px;align-items:center;min-width:150px}}
.track{{position:relative;height:8px;background:var(--track);border-radius:4px;overflow:hidden}}
.fill{{height:100%}} .good{{background:var(--good)}} .mid{{background:var(--mid)}} .bad{{background:var(--bad)}}
.ci{{position:absolute;top:0;height:100%;border-left:1px solid var(--fg);border-right:1px solid var(--fg);opacity:.35}}
.cell small{{grid-column:1/3;color:var(--mute)}} .na{{color:var(--mute)}}
ul{{font-family:system-ui,sans-serif;font-size:13px;color:var(--mute)}}
</style></head><body><main>
<h1>UK Legal AI Hallucination Audit</h1>
<p class="sub">Accuracy of large language models on the law of England and Wales. Bars show the point estimate; the bracket shows the 95% Wilson interval. Unreviewed items use automatic labels and are provisional.</p>
<div class="wrap"><table><thead><tr><th>Metric</th>{heads}</tr></thead><tbody>{rows}</tbody></table></div>
<ul>{status}</ul></main></body></html>"""
