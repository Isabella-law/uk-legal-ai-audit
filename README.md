# UK Legal AI Hallucination Audit

**Live site and citation checker: https://isabella-law.github.io/uk-legal-ai-audit/**

How reliable are large language models on the law of England and Wales? This repository contains two studies:

1. **Hallucination Audit.** 66 questions across 6 categories. Every citation a model produces is checked
   automatically against The National Archives' *Find Case Law*, and anything doubtful goes to a blind manual review.
2. **AI Judge.** Models decide real UK Supreme Court appeals handed down *after* their training cutoff, working
   from outcome-free briefs. They are scored against what the Court actually decided.

Everything runs locally. The only network calls go to the model APIs you configure and to Find Case Law.

---

## Setup (once)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[all,dev]"
cp config/models.example.json config/models.json   # edit model ids + knowledge cutoffs
export ANTHROPIC_API_KEY=...   # and OPENAI_API_KEY / GEMINI_API_KEY for the models you enable
pytest -q                      # offline self-test using a mock model
```

## Study 1: the audit

```bash
ulb check-questions        # validates the bank against Find Case Law (gold citations real, fake cases fake)
ulb run --limit 5          # cheap smoke test first
ulb run --repeats 3        # full run, resumable: re-run the same command after any interruption
ulb score                  # auto-label + verify every citation
ulb review citations       # blind: confirm each suspect citation (fabricated / misattributed / real)
ulb review answers         # blind: grade answers that need legal judgement
ulb report                 # results/report.md, report.html, summary.csv, citations.csv
```

### Question categories

| Category | n | What it tests | Scoring |
|---|---|---|---|
| `citation_recall` | 26 | Can it cite a leading case correctly? | automatic |
| `holding` | 10 | Does it state the ratio correctly? | manual 0–2 against a marking guide |
| `overruled_trap` | 10 | Question assumes law that has since changed (Ghosh, Tinsley, Caldwell…) | auto first pass + manual |
| `fabricated_trap` | 8 | Asks about a case or provision that does not exist | auto first pass + manual |
| `jurisdiction_trap` | 7 | US or Scots law bleeding in (Miranda, "not proven", punitive damages) | manual |
| `problem_question` | 5 | Realistic advice; every citation is extracted and verified | manual + citation audit |

**All questions start as `"status": "draft"`.** Before the final run, check every marking guide yourself and set
`"status": "verified"`, then run with `--verified-only`.

### How citation verification works

| Verdict | Meaning |
|---|---|
| `VERIFIED` | The neutral citation resolves on Find Case Law and the case name matches (or it's in the confirmed reference list) |
| `VERIFIED_FOOTPRINT` | Not directly resolvable, but other judgments cite this citation together with this party name |
| `NAME_MISMATCH` | The citation exists but belongs to a different case: possible fake name on a real number |
| `CITED_NAME_UNKNOWN` | The citation exists, but no case name was given, so the pairing can't be checked |
| `NOT_FOUND` | No trace on Find Case Law: likely fabricated |

Only `VERIFIED*` counts as confirmed without a human. Everything else goes to `ulb review citations`.
Known gaps: Find Case Law does not hold every judgment (e.g. *Ivey* and *Jogee* are missing; House of Lords
judgments are not held), which is why the footprint tier exists. Reviewed labels always override automatic ones.

## Study 2: the AI Judge

```bash
# write briefs in data/judge_cases/ (see the README there), set status "verified"
ulb judge run                         # only cases decided after each model's cutoff
ulb judge run --include-contaminated  # optional: compare against pre-cutoff cases (memorisation effect)
ulb judge score                       # outcome accuracy vs majority baseline, issue accuracy, Brier score
ulb judge pack                        # blind packets + ratings.csv for reasoning-quality rating
ulb judge unblind --ratings results/judge/blind/ratings.csv
```

## Research hygiene built in
* Identical fixed system prompt for every model; its hash is stored with every answer.
* No silent model fallbacks: a refusal is recorded as a refusal.
* Blind, shuffled review; model names hidden by default.
* Auto-label vs human agreement is reported (it measures how reliable the cheap checker is).
* 95% Wilson intervals on every proportion; `--repeats` for run-to-run variance.
* Find Case Law requests are cached, rate-limited and identified with a research user agent.

## Licensing note
Find Case Law content is under the Open Justice Licence. This tool only checks whether individual citations
exist and what they are titled. Before running bulk computational analysis of the corpus itself, read The
National Archives' guidance on whether you need a transactional licence:
https://caselaw.nationalarchives.gov.uk/re-use-find-case-law-records/

## Layout
```
src/ulb/      citations.py (extract)  verify.py (Find Case Law)  run.py  score.py  review.py  report.py  judge.py
data/         questions.jsonl  reference_citations.jsonl  judge_cases/
config/       models.example.json  models.mock.json
paper/        paper.md (draft with methods written; results to fill)
results/      outputs (git-ignored)
```

---

## Pilot results (3 November 2026)

The first pilot ran Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5 on the full bank (198 answers, 644 citations) and on 8 Supreme Court appeals decided July–October 2026.

**Headline findings**
- No invented cases.
- Real cases with wrong references: 3.7% (Haiku), 2.8% (Sonnet), 0% (Opus).
- Opus decided 8/8 unseen appeals as the Court did, against a baseline of 62.5%.

**Where to find it**
- Paper: `paper/paper.md`
- Showcase site: `site/index.html` (rebuild with `python3 site/build.py`)
- Run logs, with the serving model and tool calls of every run: `pilot/`

The method deviations (sub-agent runs, batched prompts, provisional grading by an AI reviewer) are set out in §3.2 and §7 of the paper.

## Website (`app/`)

The public site is a React app (Vite and Framer Motion) with a live citation checker. The checker is a browser port of `src/ulb/citations.py` and `src/ulb/verify.py`, and it queries Find Case Law directly from the visitor's browser. Every push to `main` deploys it to GitHub Pages through `.github/workflows/deploy.yml`.

```bash
cd app && npm install && npm run dev
```
