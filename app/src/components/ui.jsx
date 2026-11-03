import { useEffect, useRef, useState } from "react";
import { motion, useInView, useReducedMotion, animate } from "framer-motion";

export const MODELS = ["claude-haiku", "claude-sonnet", "claude-opus"];
export const LABEL = { "claude-haiku": "Haiku 5.5", "claude-sonnet": "Sonnet 5.5", "claude-opus": "Opus 5.5" };
export const OUT = { allowed: "Allowed", dismissed: "Dismissed", allowed_in_part: "Allowed in part" };

/* Glass panel with a soft light that follows the pointer. */
export function Glass({ as: Tag = "div", className = "", children, ...rest }) {
  const ref = useRef(null);
  const onMove = e => {
    const r = ref.current.getBoundingClientRect();
    ref.current.style.setProperty("--mx", `${e.clientX - r.left}px`);
    ref.current.style.setProperty("--my", `${e.clientY - r.top}px`);
  };
  return <Tag ref={ref} onPointerMove={onMove} className={`glass spot ${className}`} {...rest}>{children}</Tag>;
}

/* Fades and lifts content into view once. Visible immediately if motion is reduced. */
export function Reveal({ children, delay = 0, className = "", y = 24 }) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div className={className} initial={{ opacity: 0.001, y }} whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.8, delay, ease: [0.16, 1, 0.3, 1] }}>
      {children}
    </motion.div>
  );
}

export function CountUp({ to, suffix = "", decimals = 0 }) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  const [v, setV] = useState(reduce ? to : 0);
  useEffect(() => {
    if (!inView || reduce) { if (reduce) setV(to); return; }
    const c = animate(0, to, { duration: 1.6, ease: [0.16, 1, 0.3, 1], onUpdate: setV });
    return () => c.stop();
  }, [inView, to, reduce]);
  return <span ref={ref} className="num">{v.toFixed(decimals)}{suffix}</span>;
}

export function Bar({ value, good = true }) {
  const reduce = useReducedMotion();
  return (
    <div className={`bar ${good ? "good" : "badbar"}`}>
      <motion.i initial={{ width: reduce ? `${value * 100}%` : 0 }} whileInView={{ width: `${Math.max(value * 100, value > 0 ? 1.5 : 0)}%` }}
        viewport={{ once: true }} transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }} />
    </div>
  );
}

export function SectionHead({ eyebrow, title, children }) {
  return (
    <Reveal className="stack narrow">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      {children && <p className="lede">{children}</p>}
    </Reveal>
  );
}
