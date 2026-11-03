import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Glass, LABEL, MODELS, SectionHead } from "./ui.jsx";

const CAT = { citation_recall: "Citation recall", holding: "Holding", overruled_trap: "Overruled law", fabricated_trap: "Fake authority",
  jurisdiction_trap: "Jurisdiction", problem_question: "Problem question" };
const STATUS = { real: ["verified", "v-ok"], wrong: ["wrong reference", "v-bad"], fabricated: ["fabricated", "v-bad"],
  unknown: ["unverifiable", "v-warn"], unverifiable: ["unverifiable", "v-warn"] };
const good = g => ["2", "p"].includes(g);
const mid = g => ["1", "h"].includes(g);
const gsym = g => ({ p: "✓", h: "½", f: "✗" }[g] ?? g);
const gstyle = g => good(g) ? { color: "var(--ok)", background: "rgba(94,234,212,.1)" } : mid(g)
  ? { color: "var(--warn)", background: "rgba(251,191,36,.1)" } : { color: "var(--bad)", background: "rgba(251,113,133,.12)" };

function Question({ q }) {
  const [open, setOpen] = useState(false);
  const [m, setM] = useState(MODELS[0]);
  const a = q.ans[m];
  return (
    <Glass className="acc">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="qid">{q.id} · {CAT[q.cat]}</span>
        <span className="small">{q.p}</span>
        <span className="grades">{MODELS.map(x => <span key={x} className="g" style={gstyle(q.ans[x].g)} title={LABEL[x]}>{gsym(q.ans[x].g)}</span>)}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.3 }} style={{ overflow: "hidden" }}>
            <div className="body">
              {q.kp.length > 0 && <div className="stack" style={{ gap: 6 }}><p className="eyebrow">Marking guide</p><ul className="small muted" style={{ margin: 0, paddingLeft: 18 }}>{q.kp.map(k => <li key={k}>{k}</li>)}</ul></div>}
              {q.gold_cits.length > 0 && <p className="small"><span className="eyebrow">Gold citation </span>{q.gold_cits.map(c => <span key={c} className="cit" style={{ marginRight: 8 }}>{c}</span>)}</p>}
              <div className="tabs" role="tablist">{MODELS.map(x => <button key={x} role="tab" aria-selected={x === m} type="button" onClick={() => setM(x)}>{LABEL[x]}</button>)}</div>
              <div className="answer">{a.t}</div>
              {a.note && <p className={`note ${a.serious ? "serious" : ""}`}>{a.serious && <b>Serious error. </b>}{a.note}</p>}
              {a.cits.length > 0 ? (
                <div className="stack" style={{ gap: 8 }}>
                  <p className="eyebrow">Citations ({a.cits.length})</p>
                  {a.cits.map(c => (
                    <div className="citrow" key={c.c + c.n}>
                      <span className={`chip ${STATUS[c.s][1]}`}>{STATUS[c.s][0]}</span>
                      <span><span className="cit">{c.c}</span> <span className="tiny">{c.n}{c.s !== "real" && c.e ? ` · ${c.e}` : ""}</span></span>
                    </div>
                  ))}
                </div>
              ) : <p className="tiny">No citations given.</p>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Glass>
  );
}

export default function Explorer({ data }) {
  const [cat, setCat] = useState("");
  const [show, setShow] = useState("");
  const [term, setTerm] = useState("");
  const list = useMemo(() => data.questions.filter(q => {
    if (cat && q.cat !== cat) return false;
    if (show === "err" && MODELS.every(m => good(q.ans[m].g) && q.ans[m].cits.every(c => c.s === "real"))) return false;
    if (show === "cit" && !MODELS.some(m => q.ans[m].cits.some(c => c.s !== "real"))) return false;
    const t = term.trim().toLowerCase();
    return !t || (q.p + MODELS.map(m => q.ans[m].t).join(" ")).toLowerCase().includes(t);
  }), [data, cat, show, term]);
  return (
    <section className="section wrap stack" id="explorer" style={{ gap: 28 }}>
      <SectionHead eyebrow="Evidence" title="Every question, answer and citation">
        Open any question to read each model's verbatim answer, its grade with reasons, and the verdict on every citation it gave.
      </SectionHead>
      <div className="controls">
        <label htmlFor="f-cat">Category
          <select id="f-cat" value={cat} onChange={e => setCat(e.target.value)}><option value="">All categories</option>{Object.entries(CAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        </label>
        <label htmlFor="f-show">Show
          <select id="f-show" value={show} onChange={e => setShow(e.target.value)}><option value="">All questions</option><option value="err">Any model made an error</option><option value="cit">Has a flagged citation</option></select>
        </label>
        <label htmlFor="f-q">Search<input id="f-q" type="search" placeholder="Case name or citation" value={term} onChange={e => setTerm(e.target.value)} /></label>
      </div>
      <p className="tiny">{list.length} of {data.questions.length} questions · grades shown for Haiku, Sonnet, Opus</p>
      <div className="stack" style={{ gap: 10 }}>{list.map(q => <Question key={q.id} q={q} />)}</div>
    </section>
  );
}
