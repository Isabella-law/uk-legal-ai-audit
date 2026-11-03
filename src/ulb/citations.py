"""Extract and normalise English/UK legal citations from free text.

Two families are handled:
  * Neutral citations, e.g. [2016] UKSC 42, [2020] EWCA Crim 575, [2013] EWHC 111 (QB)
  * Law-report citations, e.g. [1932] AC 562, [1991] 1 QB 1, (1854) 9 Exch 341
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# --- neutral citations -------------------------------------------------------

# court token -> Find Case Law URL path (year/number appended)
_SIMPLE_COURTS = {
    "UKSC": "uksc",
    "UKPC": "ukpc",
    "UKHL": "ukhl",
    "EWCA Civ": "ewca/civ",
    "EWCA Crim": "ewca/crim",
    "EWFC": "ewfc",
    "EAT": "eat",
    "EWCOP": "ewcop",
}
# EWHC / UKUT / UKFTT need a division suffix in brackets
_DIVISIONS = {
    "EWHC": {
        "Ch": "ch", "QB": "qb", "KB": "kb", "Admin": "admin", "Comm": "comm",
        "Fam": "fam", "TCC": "tcc", "Pat": "pat", "IPEC": "ipec",
        "Admlty": "admlty", "SCCO": "scco", "Costs": "costs",
    },
    "UKUT": {"IAC": "iac", "LC": "lc", "TCC": "tcc", "AAC": "aac"},
    "UKFTT": {"TC": "tc", "GRC": "grc"},
}

_NEUTRAL_RE = re.compile(
    r"\[(?P<year>(?:19|20)\d{2})\]\s+"
    r"(?P<court>UKSC|UKPC|UKHL|EWCA\s+Civ|EWCA\s+Crim|EWHC|EWFC|EWCOP|EAT|UKUT|UKFTT)\s+"
    r"(?P<num>\d{1,5})"
    r"(?:\s*\((?P<div>[A-Za-z]+)\))?"
)

# --- law report citations ----------------------------------------------------

_REPORT_SERIES = [
    "AC", "QB", "KB", "Ch", "Fam", "WLR", "All ER", "All ER \\(Comm\\)",
    "Lloyd's Rep", "Lloyd’s Rep", "IRLR", "ICR", "BCLC", "BCC", "Cr App R",
    "P & CR", "P&CR", "EG", "EGLR", "FLR", "Fam Law", "HLR", "Med LR",
    "PNLR", "BLR", "Con LR", "App Cas", "QBD", "ChD", "Ch D", "Exch", "Ex",
    "HL Cas", "B & Ald", "M & W", "Bing", "KB", "LR", "TLR", "Cr App R \\(S\\)",
]
_SERIES_ALT = "|".join(sorted(_REPORT_SERIES, key=len, reverse=True))
_REPORT_RE = re.compile(
    r"(?P<yb>[\[\(])(?P<year>1[5-9]\d{2}|20\d{2})[\]\)]\s+"
    r"(?:(?P<vol>\d{1,3})\s+)?"
    r"(?P<series>" + _SERIES_ALT + r")\s+"
    r"(?P<page>\d{1,5})"
)

# words that carry no identifying information in a case name
_STOP = {
    "r", "v", "the", "and", "of", "on", "application", "ltd", "limited", "plc",
    "llp", "llc", "inc", "co", "company", "others", "another", "anor", "ors",
    "in", "re", "ex", "parte", "for", "a", "an", "bv", "uk", "&", "council",
    "secretary", "state", "chief", "constable", "police", "commissioners",
    "his", "her", "majesty's", "majesty", "revenue", "customs", "regina", "rex",
}


@dataclass
class Citation:
    raw: str
    kind: str  # "neutral" | "report"
    norm: str
    year: int
    court: str | None = None
    number: int | None = None
    division: str | None = None
    fcl_path: str | None = None  # Find Case Law path, neutral only
    case_name_guess: str | None = None
    start: int = 0
    end: int = 0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _clean_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def normalise(cit: str) -> str:
    """Canonical string form used for comparisons."""
    s = _clean_ws(cit).replace("’", "'")
    s = re.sub(r"\(\s*", "(", s)
    s = re.sub(r"\s*\)", ")", s)
    return s


def _fcl_path(court: str, year: int, num: int, div: str | None) -> str | None:
    court = _clean_ws(court)
    if court in _SIMPLE_COURTS:
        return f"{_SIMPLE_COURTS[court]}/{year}/{num}"
    if court in _DIVISIONS and div:
        d = _DIVISIONS[court].get(div)
        if d:
            return f"{court.lower()}/{d}/{year}/{num}"
    return None


# "Patel v Mirza", "R (Miller) v Prime Minister", "Caparo Industries plc v Dickman"
_NAME_BEFORE_RE = re.compile(
    r"((?:R\s*\([^)]{1,80}\)|[A-Z][\w'’.&\-]*(?:\s+(?:[A-Z][\w'’.&\-]*|of|and|&|the|de|van|von|plc|ltd|llp|\([^)]{1,40}\)))*)"
    r"\s+v\.?\s+"
    r"[A-Z][\w'’.&\-]*(?:\s+(?:[A-Z][\w'’.&\-]*|of|and|&|the|plc|Ltd|\([^)]{1,40}\)))*)"
    r"[\s,;:]*$"
)
_RE_NAME_RE = re.compile(r"((?:In\s+)?[Rr]e\s+[A-Z][\w'’\-]*(?:\s+[A-Z][\w'’\-]*)*)[\s,;:]*$")


_SIGNALS = {"see", "in", "following", "under", "applying", "per", "cf", "also", "and", "the", "as",
            "but", "contrast", "compare", "by", "after", "since", "following", "from", "approved",
            "overruling", "overruled", "distinguishing", "authority", "case", "decision", "held", "is", "was"}


def _strip_signals(name: str) -> str:
    words = name.split()
    while len(words) > 3 and words[0].lower().strip(",.;:") in _SIGNALS:
        words.pop(0)
    return " ".join(words)


def guess_case_name(text: str, start: int) -> str | None:
    """Look back from a citation for an 'X v Y' (or 'Re X') case name."""
    window = text[max(0, start - 160):start]
    window = window.replace("*", "").replace("_", "")
    # Skip over an immediately preceding parallel citation, e.g. "X v Y [2016] UKSC 42, [2017] AC 467"
    window = re.sub(r"(?:[\s,;]*[\[\(]\d{4}[\]\)][^\[\(]{0,30}?\d+(?:\s*\([A-Za-z]+\))?)+[\s,;]*$", " ", window)
    m = _NAME_BEFORE_RE.search(window)
    if m:
        return _strip_signals(_clean_ws(m.group(1)))
    m = _RE_NAME_RE.search(window)
    if m:
        return _clean_ws(m.group(1))
    return None


def extract(text: str) -> list[Citation]:
    """Return every citation found in `text`, in order, de-duplicated by norm."""
    out: list[Citation] = []
    seen: set[str] = set()

    for m in _NEUTRAL_RE.finditer(text):
        year, court, num, div = int(m["year"]), _clean_ws(m["court"]), int(m["num"]), m["div"]
        norm = normalise(f"[{year}] {court} {num}" + (f" ({div})" if div else ""))
        if norm in seen:
            continue
        seen.add(norm)
        out.append(Citation(
            raw=m.group(0), kind="neutral", norm=norm, year=year, court=court,
            number=num, division=div, fcl_path=_fcl_path(court, year, num, div),
            case_name_guess=guess_case_name(text, m.start()), start=m.start(), end=m.end(),
        ))

    for m in _REPORT_RE.finditer(text):
        yb = m["yb"]
        yc = "]" if yb == "[" else ")"
        vol = f"{m['vol']} " if m["vol"] else ""
        norm = normalise(f"{yb}{m['year']}{yc} {vol}{m['series']} {m['page']}")
        if norm in seen:
            continue
        seen.add(norm)
        out.append(Citation(
            raw=m.group(0), kind="report", norm=norm, year=int(m["year"]),
            case_name_guess=guess_case_name(text, m.start()), start=m.start(), end=m.end(),
        ))

    out.sort(key=lambda c: c.start)
    return out


def significant_tokens(name: str | None) -> set[str]:
    if not name:
        return set()
    toks = re.findall(r"[A-Za-z][A-Za-z'’\-]+", name.lower().replace("’", "'"))
    return {t.strip("'") for t in toks if t.strip("'") not in _STOP and len(t) > 2}


def names_match(a: str | None, b: str | None) -> bool | None:
    """True if two case names share an identifying party word. None if undecidable."""
    ta, tb = significant_tokens(a), significant_tokens(b)
    if not ta or not tb:
        return None
    return bool(ta & tb)


def key_party(name: str | None) -> str | None:
    """Most distinctive single word of a case name, for footprint searches."""
    toks = [t for t in re.findall(r"[A-Za-z][A-Za-z'’\-]+", name or "")
            if t.lower().strip("'") not in _STOP and len(t) > 2]
    if not toks:
        return None
    # Prefer the respondent in "R v X" style names, otherwise the first party.
    if re.match(r"^\s*R\s+v\.?\s", name or ""):
        return toks[0]
    return toks[0]
