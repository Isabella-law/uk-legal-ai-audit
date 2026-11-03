import { useEffect, useState } from "react";
import ParticleField from "./components/ParticleField.jsx";
import Checker from "./components/Checker.jsx";
import Explorer from "./components/Explorer.jsx";
import Paper from "./components/Paper.jsx";
import { SectionHead } from "./components/ui.jsx";
import { Errors, Footer, Hero, Judge, Limits, Method, Pilot, Specimen, Study1, Why } from "./components/Sections.jsx";

const NAV = [["check", "Live checker"], ["study1", "Audit"], ["study2", "AI judge"], ["explorer", "Evidence"], ["paper", "Paper"]];

export default function App() {
  const [data, setData] = useState(null);
  const [reference, setReference] = useState({});
  const [route, setRoute] = useState(location.hash === "#paper" ? "paper" : "home");

  useEffect(() => {
    const base = import.meta.env.BASE_URL;
    fetch(`${base}data.json?v=${__BUILD__}`).then(r => r.json()).then(setData);
    fetch(`${base}reference.json?v=${__BUILD__}`).then(r => r.json()).then(setReference).catch(() => {});
    const onHash = () => {
      const isPaper = location.hash === "#paper";
      setRoute(isPaper ? "paper" : "home");
      if (isPaper) window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // after returning from the paper view, scroll to the requested section
  useEffect(() => {
    if (route === "home" && data && location.hash && location.hash !== "#top") {
      requestAnimationFrame(() => document.querySelector(location.hash)?.scrollIntoView());
    }
  }, [route, data]);

  return (
    <>
      <div className="aurora" aria-hidden="true"><i /><i /><i /></div>
      <ParticleField />
      <div className="grain" aria-hidden="true" />
      <nav className="nav glass" aria-label="Sections">
        <a className="brand" href="#top">Fictitious Authorities?</a>
        {NAV.map(([id, l]) => <a key={id} href={`#${id}`} className={route === "paper" && id === "paper" ? "on" : ""}>{l}</a>)}
      </nav>
      <main className="page">
        {route === "paper" ? <Paper /> : !data ? (
          <div className="wrap hero"><p className="muted">Loading results…</p></div>
        ) : (
          <>
            <Hero data={data} />
            <Specimen />
            <Pilot />
            <section className="section wrap stack" id="check" style={{ gap: 32 }}>
              <SectionHead eyebrow="Try it · live" title="Check any AI answer against the official record">
                Paste legal text, for example an answer from ChatGPT, Claude or Gemini. Every neutral citation and law-report reference is checked live against The National Archives' Find Case Law, using the study's three-tier method.
              </SectionHead>
              <Checker data={data} reference={reference} />
              <p className="tiny">A flag means “check this by hand”. It is not proof of fabrication. Find Case Law does not hold every judgment (it holds no House of Lords judgments), which is why the checker also searches later judgments that cite the case.</p>
            </section>
            <Why />
            <Method />
            <Study1 data={data} />
            <Errors data={data} />
            <Judge data={data} />
            <Explorer data={data} />
            <Limits data={data} />
            <Footer />
          </>
        )}
      </main>
    </>
  );
}
