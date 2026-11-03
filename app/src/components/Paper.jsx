import { useEffect, useState } from "react";
import { marked } from "marked";
import { Glass, Reveal } from "./ui.jsx";

export default function Paper() {
  const [html, setHtml] = useState("");
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}paper.md?v=${__BUILD__}`, { cache: "no-cache" }).then(r => r.text()).then(md => setHtml(marked.parse(md)));
  }, []);
  return (
    <section className="section wrap narrow" style={{ margin: "0 auto" }}>
      <Reveal className="stack" >
        <a className="btn glassy chipbtn" href="#top" style={{ alignSelf: "flex-start" }}>← Back to the project</a>
        <Glass className="paper">
          {html ? <article dangerouslySetInnerHTML={{ __html: html }} /> : <p className="muted">Loading the paper…</p>}
        </Glass>
      </Reveal>
    </section>
  );
}
