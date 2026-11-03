/* Live citation checker: a browser port of ulb/citations.py and ulb/verify.py.
   Queries The National Archives' Find Case Law directly (it allows cross-origin requests).
   Three tiers: direct resolution, then citation footprint in later judgments, then flagged for review. */
const BASE = "https://caselaw.nationalarchives.gov.uk";

const SIMPLE = { UKSC: "uksc", UKPC: "ukpc", UKHL: "ukhl", "EWCA Civ": "ewca/civ", "EWCA Crim": "ewca/crim",
  EWFC: "ewfc", EAT: "eat", EWCOP: "ewcop" };
const DIV = {
  EWHC: { Ch: "ch", QB: "qb", KB: "kb", Admin: "admin", Comm: "comm", Fam: "fam", TCC: "tcc", Pat: "pat",
    IPEC: "ipec", Admlty: "admlty", SCCO: "scco", Costs: "costs" },
  UKUT: { IAC: "iac", LC: "lc", TCC: "tcc", AAC: "aac" },
  UKFTT: { TC: "tc", GRC: "grc" },
};
const NEUTRAL = /\[((?:19|20)\d{2})\]\s+(UKSC|UKPC|UKHL|EWCA\s+Civ|EWCA\s+Crim|EWHC|EWFC|EWCOP|EAT|UKUT|UKFTT)\s+(\d{1,5})(?:\s*\(([A-Za-z]+)\))?/g;
const SERIES = ["AC", "QB", "KB", "Ch", "Fam", "WLR", "All ER", "All ER \\(Comm\\)", "Lloyd's Rep", "Lloyd’s Rep", "IRLR",
  "ICR", "BCLC", "BCC", "Cr App R", "P & CR", "P&CR", "EG", "EGLR", "FLR", "Fam Law", "HLR", "Med LR", "PNLR", "BLR",
  "Con LR", "App Cas", "QBD", "ChD", "Ch D", "Exch", "Ex", "HL Cas", "B & Ald", "M & W", "Bing", "LR", "TLR",
  "Cr App R \\(S\\)", "PTSR"].sort((a, b) => b.length - a.length).join("|");
const REPORT = new RegExp("([\\[\\(])(1[5-9]\\d{2}|20\\d{2})[\\]\\)]\\s+(?:(\\d{1,3})\\s+)?(" + SERIES + ")\\s+(\\d{1,5})", "g");
const STOP = new Set(("r v the and of on application ltd limited plc llp llc inc co company others another anor ors in re ex parte " +
  "for a an bv uk & council secretary state chief constable police commissioners his her majesty's majesty revenue customs regina rex").split(" "));
const SIGNALS = new Set(("see in following under applying per cf also and the as but contrast compare by after since from approved " +
  "overruling overruled distinguishing authority case decision held is was").split(" "));
const NAME = /((?:R\s*\([^)]{1,80}\)|[A-Z][\w'’.&-]*(?:\s+(?:[A-Z][\w'’.&-]*|of|and|&|the|de|van|von|plc|ltd|llp|\([^)]{1,40}\)))*)\s+v\.?\s+[A-Z][\w'’.&-]*(?:\s+(?:[A-Z][\w'’.&-]*|of|and|&|the|plc|Ltd|\([^)]{1,40}\)))*)[\s,;:]*$/;

const ws = s => s.replace(/\s+/g, " ").trim();
const norm = s => ws(s).replace(/’/g, "'").replace(/\(\s*/g, "(").replace(/\s*\)/g, ")");

function guessName(text, start) {
  let w = text.slice(Math.max(0, start - 160), start).replace(/[*_]/g, "");
  w = w.replace(/(?:[\s,;]*[[(]\d{4}[\])][^[(]{0,30}?\d+(?:\s*\([A-Za-z]+\))?)+[\s,;]*$/, " ");
  const m = w.match(NAME);
  if (!m) return null;
  const words = ws(m[1]).split(" ");
  while (words.length > 3 && SIGNALS.has(words[0].toLowerCase().replace(/[,.;:]/g, ""))) words.shift();
  return words.join(" ");
}

export function extract(text) {
  const out = [], seen = new Set();
  for (const m of text.matchAll(NEUTRAL)) {
    const year = +m[1], court = ws(m[2]), num = +m[3], div = m[4];
    const n = norm(`[${year}] ${court} ${num}` + (div ? ` (${div})` : ""));
    if (seen.has(n)) continue;
    seen.add(n);
    let path = null;
    if (SIMPLE[court]) path = `${SIMPLE[court]}/${year}/${num}`;
    else if (DIV[court] && div && DIV[court][div]) path = `${court.toLowerCase()}/${DIV[court][div]}/${year}/${num}`;
    out.push({ kind: "neutral", norm: n, path, name: guessName(text, m.index), start: m.index });
  }
  for (const m of text.matchAll(REPORT)) {
    const close = m[1] === "[" ? "]" : ")";
    const n = norm(`${m[1]}${m[2]}${close} ${m[3] ? m[3] + " " : ""}${m[4]} ${m[5]}`);
    if (seen.has(n)) continue;
    seen.add(n);
    out.push({ kind: "report", norm: n, path: null, name: guessName(text, m.index), start: m.index });
  }
  return out.sort((a, b) => a.start - b.start);
}

const tokens = n => new Set(((n || "").toLowerCase().replace(/’/g, "'").match(/[a-z][a-z'-]+/g) || [])
  .map(t => t.replace(/^'|'$/g, "")).filter(t => !STOP.has(t) && t.length > 2));
export function namesMatch(a, b) {
  const ta = tokens(a), tb = tokens(b);
  if (!ta.size || !tb.size) return null;
  for (const t of ta) if (tb.has(t)) return true;
  return false;
}
function keyParty(n) {
  const t = (n || "").match(/[A-Za-z][A-Za-z'’-]+/g) || [];
  return t.find(x => !STOP.has(x.toLowerCase().replace(/^'|'$/g, "")) && x.length > 2) || null;
}

/* network: cached per session, gently rate-limited */
const cache = new Map();
let next = 0;
async function get(url) {
  if (cache.has(url)) return cache.get(url);
  const wait = Math.max(0, next - Date.now());
  next = Date.now() + wait + 250;
  const p = new Promise(r => setTimeout(r, wait))
    .then(() => fetch(url))
    .then(async r => ({ status: r.status, ok: r.ok, text: r.ok ? await r.text() : "" }))
    .catch(() => ({ status: 0, ok: false, text: "" }));
  cache.set(url, p);
  return p;
}
const decode = s => { const t = document.createElement("textarea"); t.innerHTML = s; return t.value; };
async function lookup(path) {
  const r = await get(`${BASE}/${path}/data.xml`);
  if (r.status === 404) return { status: "missing" };
  if (!r.ok) return { status: "error" };
  const m = r.text.match(/<FRBRname value="([^"]*)"/);
  return { status: "found", name: m ? decode(m[1]).trim() : null };
}
async function footprint(...terms) {
  const q = terms.map(t => `"${t}"`).join(" ");
  const r = await get(`${BASE}/atom.xml?query=${encodeURIComponent(q)}&per_page=1`);
  if (!r.ok) return null;
  const entries = (r.text.match(/<entry>/g) || []).length;
  if (!entries) return 0;
  const last = r.text.match(/page=(\d+)" rel="last"/);
  return last ? +last[1] : entries;
}
const searchUrl = (...terms) => `${BASE}/search?query=${encodeURIComponent(terms.map(t => `"${t}"`).join(" "))}`;
const plural = n => (n === 1 ? "" : "s");

export async function verify(c, reference = {}) {
  const res = { ...c, verdict: null, fcl: null, why: "", link: searchUrl(c.norm), tier: null };
  if (reference[c.norm]) {
    res.fcl = reference[c.norm];
    const nm = namesMatch(c.name, res.fcl);
    res.tier = "Reference list";
    res.verdict = nm === false ? "mismatch" : "verified";
    res.why = nm === false ? `This citation belongs to ${res.fcl}.` : `Confirmed citation for ${res.fcl}.`;
    return res;
  }
  if (c.kind === "neutral" && c.path) {
    const d = await lookup(c.path);
    if (d.status === "found") {
      res.fcl = d.name;
      res.link = `${BASE}/${c.path}`;
      res.tier = "Tier 1 · direct";
      const nm = namesMatch(c.name, d.name);
      if (nm !== false) {
        res.verdict = "verified";
        res.why = `Resolves on Find Case Law to ${d.name}.`;
        return res;
      }
      const party = keyParty(c.name);
      const fp = party ? await footprint(c.norm, party) : 0;
      if (fp) {
        res.verdict = "verified";
        res.why = `Filed as ${d.name}, and cited with “${party}” in ${fp} later judgment${plural(fp)}, so it is probably a joined appeal.`;
      } else {
        res.verdict = "mismatch";
        res.why = `This citation belongs to a different case: ${d.name}.`;
      }
      return res;
    }
    if (d.status === "error") {
      res.verdict = "error";
      res.why = "Find Case Law did not respond. Try again.";
      return res;
    }
  }
  res.tier = "Tier 2 · footprint";
  const n = await footprint(c.norm);
  if (n === null) { res.verdict = "error"; res.why = "Find Case Law did not respond. Try again."; return res; }
  if (n === 0) {
    res.verdict = "notfound";
    res.why = "No trace on Find Case Law, and no later judgment cites it. Check it by hand before relying on it.";
    return res;
  }
  const party = keyParty(c.name);
  if (!party) {
    res.verdict = "unclear";
    res.why = `Cited in ${n} judgment${plural(n)}, but no case name was given to check it against.`;
    return res;
  }
  const np = await footprint(c.norm, party);
  if (np === null) { res.verdict = "error"; res.why = "Find Case Law did not respond. Try again."; }
  else if (np > 0) {
    res.verdict = "verified";
    res.why = `Cited together with “${party}” in ${np} later judgment${plural(np)}.`;
    res.link = searchUrl(c.norm, party);
  } else {
    res.verdict = "mismatch";
    res.why = `The reference exists, but no judgment cites it with “${party}”. It may belong to another case.`;
  }
  return res;
}
