"""Run the question bank against every configured model. Resumable: completed
(model, question, repeat) triples are skipped, so you can stop and restart freely."""
from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from . import providers
from .io import append_jsonl, load_models, read_jsonl

# Fixed for every model and every question. Changing it invalidates comparisons,
# so its hash is stored with each result.
SYSTEM_PROMPT = (
    "You are assisting a trainee solicitor in England and Wales. Answer the question "
    "accurately under the law of England and Wales. Where you rely on case law or "
    "legislation, give full citations (neutral citation and/or law report reference). "
    "Be concise."
)
SYSTEM_HASH = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:12]


def raw_path(results_dir: Path, model_name: str) -> Path:
    return results_dir / "raw" / f"{model_name}.jsonl"


def run(questions_path: str, models_path: str, results_dir: str = "results",
        only_models: list[str] | None = None, repeats: int = 1, workers: int = 4,
        include_draft: bool = True, limit: int | None = None) -> None:
    results = Path(results_dir)
    qs = read_jsonl(questions_path)
    if not include_draft:
        qs = [q for q in qs if q.get("status") == "verified"]
    if limit:
        qs = qs[:limit]
    models = load_models(models_path, only_models)
    if not models:
        raise SystemExit("No enabled models in config.")

    for m in models:
        out = raw_path(results, m["name"])
        done = {(r["qid"], r["repeat"]) for r in read_jsonl(out) if not r.get("error")}
        todo = [(q, k) for q in qs for k in range(repeats) if (q["id"], k) not in done]
        print(f"[{m['name']}] {len(todo)} to run ({len(done)} already done)")
        if not todo:
            continue
        prov = providers.make(m)

        def task(q, k):
            res = prov.complete(SYSTEM_PROMPT, q["prompt"])
            return {"qid": q["id"], "model": m["name"], "model_id": m.get("model"),
                    "repeat": k, "system_hash": SYSTEM_HASH,
                    "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **res}

        n_err = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(task, q, k) for q, k in todo]
            for i, f in enumerate(as_completed(futs), 1):
                row = f.result()
                append_jsonl(out, row)
                if row["error"]:
                    n_err += 1
                    print(f"  ! {row['qid']}: {row['error'][:120]}")
                if i % 10 == 0 or i == len(futs):
                    print(f"  {i}/{len(futs)}")
        if n_err:
            print(f"  {n_err} errors - re-run the same command to retry them.")
        time.sleep(0.1)
