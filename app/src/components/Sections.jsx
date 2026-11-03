import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bar, CountUp, Glass, LABEL, MODELS, OUT, Reveal, SectionHead } from "./ui.jsx";

const REPO = "https://github.com/Isabella-law/uk-legal-ai-audit";

export function Hero({ data }) {
  const cits = data.questions.flatMap(q => MODELS.flatMap(m => q.ans[m].cits));
  const wrong = cits.filter(c => c.s === "wrong").length;
  const fab = cits.filter(c => c.s === "fabricated").length;
  const opus = data.cases.filter(c => c.preds["claude-opus"].o === c.actual).length;
  return (
    <header className="wrap hero" id="top">
      <Reveal><p className="eyebrow">Working paper · pilot results · November 2026</p></Reveal>
      <Reveal delay={0.05}><h1>Fictitious<br /><em className="shine">Authorities?</em></h1></Reveal>
      <Reveal delay={0.15}>
        <p className="lede">An empirical audit of how AI models cite the law of England and Wales, checked against the official record. It includes a live checker you can try, and a test of whether AI can decide Supreme Court appeals it has never seen.</p>
      </Reveal>
      <Reveal delay={0.2}><p className="small muted">By <span style={{ color: "var(--ink)" }}>Isabella O'Gorman</span> · LLB, City St George's, University of London</p></Reveal>
      <Reveal delay={0.25} className="ctas">
        <a className="btn primary" href="#check">Try the live checker</a>
        <a className="btn glassy" href="#paper">Read the paper</a>
        <a className="btn glassy" href={REPO} target="_blank" rel="noopener noreferrer">Code ↗</a>
      </Reveal>
      <div className="grid g4" style={{ marginTop: 18 }}>
        {[[cits.length, "AI citations checked against Find Case Law", ""], [fab, "invented cases found", "ok"],
          [wrong, "real cases given the wrong reference", "bad"], [opus, "unseen 2026 appeals Opus decided as the Court did, out of 8", "ok"]].map(([n, l, c], i) => (
          <Reveal key={l} delay={0.3 + i * 0.08}><Glass className={`stat ${c}`}><b><CountUp to={n} /></b><span>{l}</span></Glass></Reveal>
        ))}
      </div>
    </header>
  );
}

export function Specimen() {
  return (
    <Reveal className="wrap">
      <Glass className="pad specimen">
        <p className="eyebrow">One citation, checked</p>
        <div className="spec-row"><span className="spec-k">Model wrote</span><span><span className="case">Philipp v Barclays Bank UK plc</span> <span className="cit">[2023] UKSC 25</span>, <span className="cit strike">[2024] AC 1</span></span></div>
        <div className="spec-row"><span className="spec-k">The record</span><span className="muted"><span className="cit">[2024] AC 1</span> exists, but no judgment cites it with “Philipp”. <span className="cit" style={{ color: "var(--ok)" }}>[2024] AC 346</span> is cited with “Philipp” in two judgments.</span></div>
        <div className="spec-row"><span className="spec-k">Verdict</span><span><span className="chip v-bad">Real case, wrong reference</span></span></div>
      </Glass>
    </Reveal>
  );
}

export function Pilot() {
  return (
    <Reveal className="wrap" >
      <Glass className="pad" style={{ borderColor: "rgba(251,191,36,0.3)", marginTop: 18 }}>
        <p className="small"><b style={{ color: "var(--warn)" }}>Pilot study.</b> <span className="muted">Three models from one family were tested: Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5. Prompts were batched. Answer grades are provisional and were assigned by an AI reviewer, pending blind human re-grading. All raw outputs and evidence are published below.</span></p>
      </Glass>
    </Reveal>
  );
}

export function Why() {
  return (
    <section className="section wrap" id="why">
      <SectionHead eyebrow="Why it matters" title="Courts are already dealing with AI-invented case law">
        In R (Ayinde) v London Borough of Haringey [2025] EWHC 1383 (Admin), the Divisional Court addressed fictitious authorities in proceedings, and judges were still citing it this month. Yet nobody had measured, in public and repeatably, how often current models get English citations wrong, or in what way.
      </SectionHead>
    </section>
  );
}

export function Method() {
  const tiers = [
    ["Tier 1 · direct", "Resolve the neutral citation", <>For example, <span className="cit">[2016] UKSC 42</span> opens <span className="case">Patel v Mirza</span>. The party name must match.</>],
    ["Tier 2 · footprint", "Look for it in later judgments", <>Find Case Law is missing <span className="case">Ivey</span>, <span className="case">Jogee</span> and every House of Lords judgment. A real citation is still cited by later judges, under its party name. An invented one is not.</>],
    ["Tier 3 · review", "Check whatever is left by hand", <>Name mismatches and citations with no trace are reviewed by hand. Each verdict records its evidence: the counts, the correct reference, and the case that actually holds the number.</>],
  ];
  return (
    <section className="section wrap stack" id="method" style={{ gap: 40 }}>
      <SectionHead eyebrow="Method" title="Every citation goes through three checks">
        Each answer is scanned for neutral citations and law-report references. Each one is then checked against The National Archives' Find Case Law service.
      </SectionHead>
      <div className="grid g3 flow">
        {tiers.map(([n, t, d], i) => (
          <Reveal key={n} delay={i * 0.12}><Glass className="tier"><span className="n">{n}</span><h3>{t}</h3><p className="small muted">{d}</p></Glass></Reveal>
        ))}
      </div>
    </section>
  );
}

const pct = v => `${(v * 100).toFixed(1)}%`;
export function Study1({ data }) {
  const S = Object.fromEntries(data.summary.map(r => [r.model, r]));
  const rows = [
    ["cit_fabricated", "Invented cases", false, "pct"], ["cit_misattributed", "Real case, wrong reference", false, "pct"],
    ["citation_recall", "Citation recall", true, "frac"], ["fabricated_trap", "Fake authority flagged", true, "frac"],
    ["overruled_trap", "Overruled law caught", true, "frac"], ["quality", "Answer quality", true, "pct"], ["serious_error", "Serious legal errors", false, "frac"],
  ];
  return (
    <section className="section wrap stack" id="study1" style={{ gap: 40 }}>
      <SectionHead eyebrow="Study 1 · 66 questions × 3 models · 644 citations" title={<>No invented cases. <span className="shine">Wrong references</span> instead.</>}>
        The questions test six failure modes: citation recall, stating the holding, overruled law (Ghosh, Tinsley, Caldwell, Anns), authorities that do not exist, US and Scots law leaking in, and realistic problem questions.
      </SectionHead>
      <div className="grid g3">
        {MODELS.map((m, i) => (
          <Reveal key={m} delay={i * 0.1}>
            <Glass className="model">
              <header><span className="name">{LABEL[m]}</span><span className="tiny">{S[m].citations} citations</span></header>
              {rows.map(([k, l, good, fmt]) => {
                const p = +S[m][k + "_p"];
                return (
                  <div className="metric" key={k}>
                    <div className="top"><span className="muted">{l}</span><b style={{ color: (good ? p >= 0.95 : p === 0) ? "var(--ok)" : (good ? "var(--ink)" : "var(--bad)") }}>{fmt === "pct" ? pct(p) : `${S[m][k + "_k"]}/${S[m][k + "_n"]}`}</b></div>
                    <Bar value={p} good={good} />
                  </div>
                );
              })}
            </Glass>
          </Reveal>
        ))}
      </div>
      <p className="tiny">95% Wilson intervals are in the downloadable summary. Answer quality is the percentage of available marks on the holding, jurisdiction and problem questions.</p>
    </section>
  );
}

export function Errors({ data }) {
  const seen = new Set(), errs = [];
  data.questions.forEach(q => MODELS.forEach(m => q.ans[m].cits.forEach(c => {
    if (c.s === "wrong" && !seen.has(c.c)) { seen.add(c.c); errs.push({ ...c, m }); }
  })));
  return (
    <section className="section wrap stack" id="errors" style={{ gap: 40 }}>
      <SectionHead eyebrow="Error gallery" title="The mistakes a lazy check would pass">
        Each of these cases is real, so checking that the case exists would pass all of them. The reference is wrong, so anyone who looks it up finds a different case.
      </SectionHead>
      <div className="grid g3">
        {errs.map((e, i) => (
          <Reveal key={e.c} delay={(i % 3) * 0.08}>
            <Glass className="err">
              <span className="case">{e.n}</span>
              <div className="line"><span className="cit strike">{e.c}</span><span className="tiny">{LABEL[e.m]}</span></div>
              <p className="small muted">{e.e}</p>
            </Glass>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

export function Judge({ data }) {
  const [open, setOpen] = useState(null);
  const score = m => data.cases.filter(c => c.preds[m].o === c.actual).length;
  return (
    <section className="section wrap stack" id="study2" style={{ gap: 40 }}>
      <SectionHead eyebrow="Study 2 · the AI judge" title="Eight real appeals the models had never seen">
        These Supreme Court judgments were handed down between July and October 2026, after the models' training cutoffs. Each model received an outcome-free brief (anonymised facts, neutral issues, both sides' submissions) and decided the appeal. Always predicting “allowed” would score 5 out of 8.
      </SectionHead>
      <div className="grid g4">
        <Reveal><Glass className="stat"><b>5/8</b><span>baseline: always “allowed”</span></Glass></Reveal>
        {MODELS.map((m, i) => (
          <Reveal key={m} delay={0.08 * (i + 1)}><Glass className={`stat ${score(m) === 8 ? "ok" : score(m) < 5 ? "bad" : ""}`}><b><CountUp to={score(m)} />/8</b><span>{LABEL[m]}</span></Glass></Reveal>
        ))}
      </div>
      <Reveal>
        <Glass className="tablewrap">
          <table>
            <thead><tr><th>Appeal</th><th>Decided</th><th>The Court</th>{MODELS.map(m => <th key={m}>{LABEL[m]}</th>)}</tr></thead>
            <tbody>
              {data.cases.map(c => (
                <tr key={c.id}>
                  <th><span className="case">{c.title}</span><br /><a className="cit" href={c.url} target="_blank" rel="noopener noreferrer">{c.cit}</a></th>
                  <td className="tiny">{new Date(c.date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</td>
                  <td><b>{OUT[c.actual]}</b> <span className="tiny">{c.maj}</span></td>
                  {MODELS.map(m => {
                    const p = c.preds[m], hit = p.o === c.actual;
                    return <td key={m}><span className={`chip ${hit ? "v-ok" : "v-bad"}`}>{OUT[p.o]}</span><div className="tiny" style={{ marginTop: 4 }}>confidence {p.conf}{p.rec ? " · recognised" : ""}</div></td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </Glass>
      </Reveal>
      <p className="small muted">“Recognised” means the model said it believed it already knew the case. Opus scored 5/5 on the cases it did not claim to recognise. Haiku predicted “dismissed” six times, though the Court dismissed only three appeals, which suggests a bias towards upholding the court below.</p>
      <div className="stack" style={{ gap: 10 }}>
        <h3>Read the AI judgments</h3>
        {data.cases.map(c => (
          <Glass key={c.id} className="acc">
            <button type="button" aria-expanded={open === c.id} onClick={() => setOpen(open === c.id ? null : c.id)}>
              <span className="qid">{c.cit}</span><span className="case">{c.title}</span><span className="muted">{open === c.id ? "−" : "+"}</span>
            </button>
            <AnimatePresence initial={false}>
              {open === c.id && (
                <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.35 }} style={{ overflow: "hidden" }}>
                  <div className="body">
                    <p className="small"><b>What the Court held.</b> <span className="muted">{c.summary}</span></p>
                    {MODELS.map(m => (
                      <div key={m} className="stack" style={{ gap: 8 }}>
                        <div className="row"><b>{LABEL[m]}</b><span className={`chip ${c.preds[m].o === c.actual ? "v-ok" : "v-bad"}`}>{OUT[c.preds[m].o]}</span></div>
                        <div className="answer">{c.preds[m].t}</div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </Glass>
        ))}
      </div>
    </section>
  );
}

export function Limits({ data }) {
  const served = [...new Set(data.runs.flatMap(r => r.served))].join(", ");
  const clean = data.runs.every(r => !r.forbidden) && data.judge_runs.every(r => !r.forbidden);
  return (
    <section className="section wrap stack" id="limits" style={{ gap: 28 }}>
      <SectionHead eyebrow="Limits" title="What this pilot cannot show yet" />
      <div className="grid g2">
        {[["Scale", "One model family and one run per question. The full protocol (one question per API call, three repeats, GPT and Gemini models) is built into the tool."],
          ["Marking", "Answer quality was marked against a fixed marking guide with the assistance of a language model. The citation results do not depend on this marking: every verdict rests on the public record and is published with its evidence."],
          ["Study 2", "Only eight cases, with briefs drafted by an LLM that knew the outcome, though checked for leaks by script. Opus said it recognised three cases, probably from the lower-court stages."],
          ["Coverage", "Nine citations could not be confirmed without Westlaw or Lexis, and are reported as unverifiable rather than as correct."]].map(([t, d], i) => (
          <Reveal key={t} delay={(i % 2) * 0.08}><Glass className="pad stack" style={{ gap: 8 }}><h3>{t}</h3><p className="small muted">{d}</p></Glass></Reveal>
        ))}
      </div>
      <p className="tiny">Audit trail: {data.runs.length} answer runs and {data.judge_runs.length} judge runs, served by {served}. {clean ? "No run used a forbidden tool." : "See the run log."}</p>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="foot wrap stack">
      <h2 style={{ fontSize: "clamp(1.6rem,3vw,2.2rem)" }}>Check every reference, not just the case name.</h2>
      <div className="row">
        <a className="btn primary" href="#check">Try the checker</a>
        <a className="btn glassy" href={REPO} target="_blank" rel="noopener noreferrer">Code and data ↗</a>
      </div>
      <p className="tiny">Research by Isabella O'Gorman, LLB, City St George's, University of London. Case law: The National Archives, Find Case Law, used under the Open Justice Licence.</p>
    </footer>
  );
}
