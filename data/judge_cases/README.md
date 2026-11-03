# Study 2 case briefs

One JSON file per appeal, copied from `_TEMPLATE.json`. Files starting with `_` are ignored.

## Picking cases
* UK Supreme Court judgments handed down **after the training cutoff of every model you test**
  (put each model's cutoff in `config/models.json`; the runner excludes any case on or before it).
* Aim for 30 or more cases, so the confidence intervals are meaningful. Include allowed and dismissed appeals,
  and some split decisions.
* Source: https://caselaw.nationalarchives.gov.uk/uksc (filter by date). Many UKSC cases also have a
  press summary, but **do not copy wording from the press summary or the judgment's conclusion**.

## Writing a brief without leaking the answer
1. Facts: take them from the facts section only. Anonymise the parties.
2. Issues: phrase them neutrally ("Does X apply?", not "Was the CA wrong to hold X?").
3. Submissions: give each side's argument at similar length and strength.
4. Remove any sentence that tells the reader which way the court went, including hints like "the court
   was persuaded".
5. Have someone else read it and guess the outcome; if they can tell from the drafting, rewrite it.
6. Set `"status": "verified"` only after the leakage check.
