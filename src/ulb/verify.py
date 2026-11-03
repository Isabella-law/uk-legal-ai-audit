"""Verify citations against The National Archives' Find Case Law service.

Three-tier verdict for each citation:

  VERIFIED            Neutral citation resolves on Find Case Law and the case name matches,
                      or the citation is in the curated local reference list.
  VERIFIED_FOOTPRINT  Not directly resolvable, but other judgments on Find Case Law cite this
                      exact citation together with the same party name.
  NAME_MISMATCH       The citation exists (directly or by footprint) but is attached to a
                      different case name. Possible misattribution -> manual review.
  CITED_NAME_UNKNOWN  Citation string exists in the corpus, but no case name was given
                      alongside it, so the pairing cannot be checked.
  NOT_FOUND           No trace of the citation anywhere on Find Case Law -> likely fabricated,
                      always confirmed manually.
  ERROR               Network failure; re-run later.

Results are cached on disk so re-runs are free and polite to the service.
"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
from pathlib import Path

import requests

from .citations import Citation, key_party, names_match, normalise

BASE = "https://caselaw.nationalarchives.gov.uk"
UA = "uk-legal-ai-benchmark/0.1 (academic research; citation verification)"

VERDICTS = ["VERIFIED", "VERIFIED_FOOTPRINT", "NAME_MISMATCH", "CITED_NAME_UNKNOWN", "NOT_FOUND", "ERROR"]


class Verifier:
    def __init__(self, cache_path: str | Path = "results/fcl_cache.json",
                 reference_path: str | Path | None = "data/reference_citations.jsonl",
                 delay: float = 0.4, offline: bool = False):
        self.cache_path = Path(cache_path)
        self.cache: dict = json.loads(self.cache_path.read_text()) if self.cache_path.exists() else {}
        self.delay = delay
        self.offline = offline
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA
        self.reference: dict[str, str] = {}
        if reference_path and Path(reference_path).exists():
            for line in Path(reference_path).read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r.get("verified"):  # only entries confirmed by `ulb check-questions` or by hand
                        self.reference[normalise(r["citation"])] = r["case_name"]

    # -- low level -------------------------------------------------------------
    def _save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(self.cache, indent=1, sort_keys=True))

    def _get(self, url: str) -> requests.Response | None:
        if self.offline:
            return None
        for attempt in range(4):
            try:
                time.sleep(self.delay)
                r = self.session.get(url, timeout=30)
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(2 ** (attempt + 1))
                    continue
                return r
            except requests.RequestException:
                time.sleep(2 ** (attempt + 1))
        return None

    def lookup_path(self, fcl_path: str) -> dict:
        """Resolve a neutral citation path. Returns {status: found|missing|error, name}."""
        key = f"path:{fcl_path}"
        if key in self.cache:
            return self.cache[key]
        r = self._get(f"{BASE}/{fcl_path}/data.xml")
        if r is None:
            return {"status": "error"}
        if r.status_code == 404:
            res = {"status": "missing"}
        elif r.ok:
            m = re.search(r'<FRBRname value="([^"]*)"', r.text)
            res = {"status": "found", "name": html.unescape(m.group(1)).strip() if m else None}
        else:
            return {"status": "error"}
        self.cache[key] = res
        self._save()
        return res

    def footprint(self, *terms: str) -> int | None:
        """Number of Find Case Law documents containing every quoted term (None on error)."""
        q = " ".join(f'"{t}"' for t in terms)
        key = f"fp:{q}"
        if key in self.cache:
            return self.cache[key]
        url = f"{BASE}/atom.xml?query={urllib.parse.quote(q)}&per_page=1"
        r = self._get(url)
        if r is None or not r.ok:
            return None
        n_entries = r.text.count("<entry>")
        m = re.search(r'page=(\d+)" rel="last"', r.text)
        n = int(m.group(1)) if m else n_entries
        if n_entries == 0:
            n = 0
        self.cache[key] = n
        self._save()
        return n

    # -- verdicts ----------------------------------------------------------------
    def verify(self, c: Citation) -> dict:
        claimed = c.case_name_guess
        out = {"citation": c.norm, "kind": c.kind, "claimed_name": claimed,
               "fcl_name": None, "footprint": None, "verdict": None, "method": None}

        # 0. curated reference list (gold citations from the question bank)
        if c.norm in self.reference:
            ref = self.reference[c.norm]
            out["fcl_name"] = ref
            nm = names_match(claimed, ref)
            out["verdict"] = "NAME_MISMATCH" if nm is False else "VERIFIED"
            out["method"] = "reference"
            return out

        # 1. direct resolution of neutral citations
        if c.kind == "neutral" and c.fcl_path:
            res = self.lookup_path(c.fcl_path)
            if res["status"] == "found":
                out["fcl_name"] = res.get("name")
                nm = names_match(claimed, res.get("name"))
                if nm is not False:  # match, or no name given (the citation itself is real)
                    out["verdict"], out["method"] = "VERIFIED", "direct"
                    return out
                # name disagrees: the FCL title may be a joined appeal -> check footprint
                party = key_party(claimed)
                fp = self.footprint(c.norm, party) if party else None
                out["footprint"] = fp
                out["verdict"] = "VERIFIED_FOOTPRINT" if fp else "NAME_MISMATCH"
                out["method"] = "direct+footprint"
                return out
            if res["status"] == "error":
                out["verdict"], out["method"] = "ERROR", "direct"
                return out

        # 2. footprint in later judgments
        n_cit = self.footprint(c.norm)
        if n_cit is None:
            out["verdict"], out["method"] = "ERROR", "footprint"
            return out
        out["footprint"] = n_cit
        if n_cit == 0:
            out["verdict"], out["method"] = "NOT_FOUND", "footprint"
            return out
        party = key_party(claimed)
        if not party:
            out["verdict"], out["method"] = "CITED_NAME_UNKNOWN", "footprint"
            return out
        n_pair = self.footprint(c.norm, party)
        if n_pair is None:
            out["verdict"], out["method"] = "ERROR", "footprint"
        elif n_pair > 0:
            out["verdict"], out["method"] = "VERIFIED_FOOTPRINT", "footprint"
        else:
            out["verdict"], out["method"] = "NAME_MISMATCH", "footprint"
        return out

    def name_exists(self, name: str) -> int | None:
        """Footprint of a bare case name (used to confirm fabricated-case traps are fake)."""
        return self.footprint(name)
