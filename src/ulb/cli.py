"""Command line: `ulb <command>`. Run `ulb -h` for help."""
from __future__ import annotations

import argparse
import json

from . import judge, report, review, run, score
from .citations import extract
from .verify import Verifier


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="ulb", description="UK Legal AI Hallucination Audit")
    p.add_argument("--questions", default="data/questions.jsonl")
    p.add_argument("--models", default="config/models.json")
    p.add_argument("--results", default="results")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="query models with the question bank")
    r.add_argument("--only", nargs="*", help="model names from config")
    r.add_argument("--repeats", type=int, default=1)
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--verified-only", action="store_true", help="skip questions still marked draft")
    r.add_argument("--limit", type=int)

    s = sub.add_parser("score", help="auto-score and verify citations")
    s.add_argument("--offline", action="store_true", help="use cache only, no network")

    rv = sub.add_parser("review", help="blind manual review")
    rv.add_argument("what", choices=["answers", "citations"])
    rv.add_argument("--reviewer", default="me")
    rv.add_argument("--show-models", action="store_true")
    rv.add_argument("--category")

    rp = sub.add_parser("report", help="build tables and dashboard")
    rp.add_argument("--reviewer")

    v = sub.add_parser("verify", help="check citations in a piece of text")
    v.add_argument("text")

    cq = sub.add_parser("check-questions", help="validate question bank and confirm fake cases are fake")

    j = sub.add_parser("judge", help="Study 2: AI judge")
    j.add_argument("action", choices=["run", "score", "pack", "unblind"])
    j.add_argument("--cases", default="data/judge_cases")
    j.add_argument("--only", nargs="*")
    j.add_argument("--include-draft", action="store_true")
    j.add_argument("--include-contaminated", action="store_true",
                   help="also run cases decided before the model's cutoff (for a contamination comparison)")
    j.add_argument("--repeats", type=int, default=1)
    j.add_argument("--ratings", help="filled ratings.csv for unblind")

    a = p.parse_args(argv)
    if a.cmd == "run":
        run.run(a.questions, a.models, a.results, a.only, a.repeats, a.workers,
                include_draft=not a.verified_only, limit=a.limit)
    elif a.cmd == "score":
        score.score(a.questions, a.results, offline=a.offline)
    elif a.cmd == "review":
        if a.what == "answers":
            review.review_answers(a.questions, a.results, a.reviewer, not a.show_models, a.category)
        else:
            review.review_citations(a.results, a.reviewer, not a.show_models)
    elif a.cmd == "report":
        report.build(a.questions, a.results, a.reviewer)
    elif a.cmd == "verify":
        ver = Verifier(cache_path=f"{a.results}/fcl_cache.json")
        for c in extract(a.text):
            print(json.dumps(ver.verify(c), ensure_ascii=False))
    elif a.cmd == "check-questions":
        from .qcheck import check
        check(a.questions, a.results)
    elif a.cmd == "judge":
        if a.action == "run":
            judge.run(a.cases, a.models, a.results, a.only, a.include_draft, a.include_contaminated, a.repeats)
        elif a.action == "score":
            judge.score(a.cases, a.results, a.include_draft)
        elif a.action == "pack":
            judge.pack(a.cases, a.results, a.include_draft)
        else:
            if not a.ratings:
                raise SystemExit("--ratings path/to/ratings.csv required")
            judge.unblind(a.ratings, a.results)


if __name__ == "__main__":
    main()
