# UK Legal AI Hallucination Audit: results

Values are proportions with 95% Wilson confidence intervals. Unreviewed items use automatic labels and are **provisional** until manual review is complete.

## Status

- **claude-haiku**: 66 answers, 0 refused/empty; 40/40 manually reviewed; 162/162 citations confirmed.
- **claude-opus**: 66 answers, 0 refused/empty; 40/40 manually reviewed; 236/236 citations confirmed.
- **claude-sonnet**: 66 answers, 0 refused/empty; 40/40 manually reviewed; 246/246 citations confirmed.
- Auto-label vs human agreement on trap questions: 50/54 (92.6%).

## Metrics

| Metric | claude-haiku | claude-opus | claude-sonnet |
|---|---|---|---|
| Citation recall accuracy ↑ | 96.2% (81–99) n=26 | 100.0% (87–100) n=26 | 100.0% (87–100) n=26 |
| Fake-case trap: correctly flagged ↑ | 87.5% (53–98) n=8 | 100.0% (68–100) n=8 | 100.0% (68–100) n=8 |
| Overruled-law trap: caught ↑ | 70.0% (40–89) n=10 | 100.0% (72–100) n=10 | 100.0% (72–100) n=10 |
| Answer quality (holding / jurisdiction / problem) ↑ | 84.1% (71–92) n=44 | 100.0% (92–100) n=44 | 100.0% (92–100) n=44 |
| Answers with serious legal error ↓ | 5.0% (1–17) n=40 | 0.0% (0–9) n=40 | 0.0% (0–9) n=40 |
| Citations fabricated ↓ | 0.0% (0–2) n=162 | 0.0% (0–2) n=236 | 0.0% (0–2) n=246 |
| Citations wrong (real case, wrong reference) ↓ | 3.7% (2–8) n=162 | 0.0% (0–2) n=236 | 2.8% (1–6) n=246 |
| Citations unverifiable ↓ | 1.2% (0–4) n=162 | 0.8% (0–3) n=236 | 2.4% (1–5) n=246 |
| Citations verified real ↑ | 95.1% (91–97) n=162 | 99.2% (97–100) n=236 | 94.7% (91–97) n=246 |
