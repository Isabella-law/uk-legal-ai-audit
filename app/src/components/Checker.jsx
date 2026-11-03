import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { extract, verify } from "../lib/checker.js";
import { Glass } from "./ui.jsx";

const VERDICT = {
  verified: ["Verified", "v-ok"], mismatch: ["Belongs to another case", "v-bad"], notfound: ["No trace found", "v-bad"],
  unclear: ["Exists, name unchecked", "v-warn"], error: ["Not reachable", "v-warn"], pending: ["Checking…", "v-wait"],
};

export default function Checker({ data, reference }) {
  const samples = useMemo(() => {
    const real = data.questions.find(q => q.id === "PRB-02").ans["claude-haiku"].t;
    return [
      { label: "A real AI answer from the study", text: real },
      { label: "Invented authorities", text: "The leading case is Harmon v Westbridge Estates Ltd [2019] UKSC 37, applying Caparo Industries plc v Dickman [1990] 2 AC 605. See also Okafor v Linton Housing Trust [2021] EWCA Civ 1188, and Philipp v Barclays Bank UK plc [2024] AC 1 on the Quincecare duty." },
      { label: "All correct", text: "Patel v Mirza [2016] UKSC 42, [2017] AC 467 replaced the reliance test in Tinsley v Milligan [1994] 1 AC 340. On dishonesty, see Ivey v Genting Casinos (UK) Ltd [2017] UKSC 67, applied in R v Barton and Booth [2020] EWCA Crim 575, [2021] QB 685." },
    ];
  }, [data]);
  const [text, setText] = useState(samples[1].text);
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function run() {
    const cits = extract(text);
    if (!cits.length) { setRows([]); setMsg("No citations found. Paste text containing references such as [2016] UKSC 42 or [1932] AC 562."); return; }
    setMsg(""); setBusy(true);
    setRows(cits.map(c => ({ ...c, verdict: "pending" })));
    await Promise.all(cits.map(async (c, i) => {
      const r = await verify(c, reference);
      setRows(prev => prev.map((p, j) => (j === i ? r : p)));
    }));
    setBusy(false);
  }

  const done = rows.filter(r => r.verdict !== "pending").length;
  const counts = rows.reduce((a, r) => ({ ...a, [r.verdict]: (a[r.verdict] || 0) + 1 }), {});

  return (
    <Glass className="pad stack checker">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <label htmlFor="ck" className="eyebrow">Paste legal text</label>
        <span className="tiny">Runs in your browser. Nothing is stored.</span>
      </div>
      <textarea id="ck" value={text} onChange={e => setText(e.target.value)} spellCheck={false} />
      <div className="row">
        <button className="btn primary" onClick={run} disabled={busy} type="button">
          {busy ? `Checking ${done}/${rows.length}…` : "Check citations"}
        </button>
        {samples.map((s, i) => (
          <button key={i} className="btn glassy chipbtn" type="button" onClick={() => { setText(s.text); setRows([]); setMsg(""); }}>{s.label}</button>
        ))}
      </div>
      {rows.length > 0 && (
        <div className="progress" aria-hidden="true"><i style={{ width: `${(done / rows.length) * 100}%` }} /></div>
      )}
      <div aria-live="polite" className="stack" style={{ gap: 10 }}>
        {msg && <p className="small muted">{msg}</p>}
        {rows.length > 0 && !busy && (
          <div className="row">
            <span className="small muted">{rows.length} citation{rows.length > 1 ? "s" : ""}:</span>
            {Object.entries(counts).map(([k, n]) => <span key={k} className={`chip ${VERDICT[k][1]}`}>{n} {VERDICT[k][0].toLowerCase()}</span>)}
          </div>
        )}
        <AnimatePresence initial={false}>
          {rows.map((r, i) => {
            const [label, cls] = VERDICT[r.verdict];
            return (
              <motion.div key={r.norm} layout initial={{ opacity: 0, y: 12, filter: "blur(6px)" }} animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                transition={{ duration: 0.5, delay: i * 0.05 }} className={`res ${cls === "v-bad" ? "bad" : cls === "v-ok" ? "ok" : ""}`}>
                <div>
                  <span className="cit" style={{ fontSize: "0.98rem" }}>{r.norm}</span>
                  {r.name && <span className="case muted"> · {r.name}</span>}
                </div>
                <span className={`chip ${cls}`}>{label}</span>
                {r.why && <p className="why">{r.why}</p>}
                {r.verdict !== "pending" && (
                  <div className="meta">
                    {r.tier && <span>{r.tier}</span>}
                    {r.link && <a href={r.link} target="_blank" rel="noopener noreferrer">Open on Find Case Law ↗</a>}
                  </div>
                )}
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </Glass>
  );
}
