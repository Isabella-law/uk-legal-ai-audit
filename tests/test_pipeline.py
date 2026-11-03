"""End-to-end with the mock provider and a pre-filled verifier cache (no network, no cost)."""
import json
import shutil
from pathlib import Path

from ulb import judge, report, run, score
from ulb.io import read_jsonl

ROOT = Path(__file__).resolve().parents[1]


def test_benchmark_pipeline(tmp_path):
    res = tmp_path / "results"
    run.run(str(ROOT / "data/questions.jsonl"), str(ROOT / "config/models.mock.json"), str(res), workers=2)
    assert len(read_jsonl(res / "raw/mock-a.jsonl")) == len(read_jsonl(ROOT / "data/questions.jsonl"))
    score.score(str(ROOT / "data/questions.jsonl"), str(res), offline=True)
    scored = read_jsonl(res / "scored.jsonl")
    assert scored and all("citations" in s for s in scored)
    # mock fabricates "[2019] UKSC 88"; offline it must never be marked VERIFIED
    for s in scored:
        for c in s["citations"]:
            if c["citation"] == "[2019] UKSC 88":
                assert c["verdict"] != "VERIFIED"
    table = report.build(str(ROOT / "data/questions.jsonl"), str(res))
    assert set(table) == {"mock-a", "mock-b"}
    assert (res / "report.html").read_text().startswith("<!doctype html>")


def test_judge_pipeline(tmp_path):
    cases = tmp_path / "cases"
    cases.mkdir()
    c = json.loads((ROOT / "data/judge_cases/_TEMPLATE.json").read_text())
    c.update(id="T-1", status="verified", decision_date="2025-06-01", actual_outcome="dismissed")
    (cases / "t1.json").write_text(json.dumps(c))
    res = tmp_path / "results"
    judge.run(str(cases), str(ROOT / "config/models.mock.json"), str(res))
    rows = read_jsonl(res / "judge/raw.jsonl")
    assert len(rows) == 2 and all(r["decision"]["outcome"] in judge.OUTCOMES for r in rows)
    judge.score(str(cases), str(res))
    judge.pack(str(cases), str(res))
    assert (res / "judge/blind/ratings.csv").exists()
