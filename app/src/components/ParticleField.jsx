import { useEffect, useRef } from "react";

/* A drifting "citation network": nodes are real citations from the study.
   Nodes that were wrong references glow red. Links form between nearby nodes,
   and the field leans towards the pointer. Static frame under prefers-reduced-motion. */
const GOOD = ["[2016] UKSC 42", "[1932] AC 562", "[2015] UKSC 11", "[2018] UKSC 4", "[2017] UKSC 67", "[2003] UKHL 50",
  "[1990] 2 AC 605", "[2021] UKSC 5", "[2024] UKSC 33", "[1964] AC 465", "[2015] UKSC 67", "[1985] AC 809",
  "[2023] UKSC 25", "[2019] UKSC 41", "[1893] 1 QB 256", "[2026] UKSC 36", "[2025] EWHC 1383 (Admin)", "[2016] UKSC 8"];
const BAD = ["[2024] AC 1", "[2018] UKSC 18", "[2023] ICR 1", "[2022] AC 1223", "[2013] 1 WLR 5"];

export default function ParticleField() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas.getContext("2d");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let w, h, dpr, nodes = [], raf;
    const mouse = { x: -9999, y: -9999 };

    function init() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth; h = canvas.clientHeight;
      canvas.width = w * dpr; canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.round(Math.min(110, Math.max(40, (w * h) / 16000)));
      nodes = Array.from({ length: count }, (_, i) => {
        const bad = i % 11 === 3;
        const label = i % 4 === 0 ? (bad ? BAD[i % BAD.length] : GOOD[i % GOOD.length]) : null;
        return { x: Math.random() * w, y: Math.random() * h, vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
                 r: label ? 2.2 : 1.3 + Math.random(), bad, label, phase: Math.random() * Math.PI * 2 };
      });
    }

    function frame(t) {
      ctx.clearRect(0, 0, w, h);
      const LINK = Math.min(150, w / 8);
      for (const n of nodes) {
        if (!reduce) {
          const dx = mouse.x - n.x, dy = mouse.y - n.y, d = Math.hypot(dx, dy);
          if (d < 180) { n.vx += (dx / d) * 0.012; n.vy += (dy / d) * 0.012; }
          n.vx *= 0.985; n.vy *= 0.985;
          n.vx += (Math.random() - 0.5) * 0.01; n.vy += (Math.random() - 0.5) * 0.01;
          n.x += n.vx; n.y += n.vy;
          if (n.x < -20) n.x = w + 20; if (n.x > w + 20) n.x = -20;
          if (n.y < -20) n.y = h + 20; if (n.y > h + 20) n.y = -20;
        }
      }
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i + 1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j], d = Math.hypot(a.x - b.x, a.y - b.y);
          if (d < LINK) {
            const alpha = (1 - d / LINK) * 0.22;
            ctx.strokeStyle = a.bad || b.bad ? `rgba(251,113,133,${alpha})` : `rgba(125,211,252,${alpha})`;
            ctx.lineWidth = 0.7;
            ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
          }
        }
      }
      ctx.font = "500 10px 'JetBrains Mono', ui-monospace, monospace";
      for (const n of nodes) {
        const pulse = reduce ? 1 : 0.6 + 0.4 * Math.sin(t / 900 + n.phase);
        const color = n.bad ? "251,113,133" : "94,234,212";
        ctx.fillStyle = `rgba(${color},${0.35 + 0.5 * pulse})`;
        ctx.shadowColor = `rgba(${color},0.9)`; ctx.shadowBlur = n.label ? 12 : 6;
        ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill();
        ctx.shadowBlur = 0;
        if (n.label) {
          ctx.fillStyle = `rgba(${n.bad ? "251,170,180" : "203,213,225"},${0.1 + 0.12 * pulse})`;
          ctx.fillText(n.label, n.x + 7, n.y + 3);
        }
      }
      if (!reduce) raf = requestAnimationFrame(frame);
    }

    const onMove = e => { mouse.x = e.clientX; mouse.y = e.clientY; };
    const onLeave = () => { mouse.x = -9999; mouse.y = -9999; };
    const onResize = () => { init(); if (reduce) frame(0); };
    init();
    raf = requestAnimationFrame(frame);
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerleave", onLeave);
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("resize", onResize);
    };
  }, []);
  return <canvas ref={ref} className="particles" aria-hidden="true" />;
}
