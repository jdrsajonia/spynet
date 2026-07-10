import { useState } from "react";
import { confClass, prettyDate } from "../utils/format";

// Vista "Compare Websites" (mockup workshop 2, depurado). El formulario maneja
// su estado local; los datos/loading/error y la acción llegan por props desde
// el contenedor. Se omiten Score, "Similarities & Insights" (IA) y las
// categorías inventadas (Language/Runtime/…): solo frontend/backend/cdn/server.
const CATEGORIES = ["frontend", "backend", "cdn", "server", "analytics"];

export default function CompareView({ data, loading, error, onCompare }) {
  const [a, setA] = useState("");
  const [b, setB] = useState("");

  return (
    <section>
      <header className="view-head">
        <h2 className="view-head__title">Compare Websites</h2>
        <p className="view-head__meta">Compare the stack technologies of two sites side by side.</p>
      </header>

      <div className="cmp-form">
        <input className="cmp-input" placeholder="github.com" value={a}
          onChange={(e) => setA(e.target.value)} onKeyDown={(e) => e.key === "Enter" && onCompare(a, b)} />
        <span className="cmp-vs">vs</span>
        <input className="cmp-input" placeholder="vercel.com" value={b}
          onChange={(e) => setB(e.target.value)} onKeyDown={(e) => e.key === "Enter" && onCompare(a, b)} />
        <button className="cmp-btn" onClick={() => onCompare(a, b)} disabled={loading}>
          {loading ? "…" : "Compare"}
        </button>
      </div>

      {loading && <div className="placeholder">Comparing… (It can analyse in live if does not exist previous data)</div>}
      {error && <div className="error">{error}</div>}
      {data && <Results data={data} />}
    </section>
  );
}

function Results({ data }) {
  const { a, b, comparison } = data;
  return (
    <>
      <div className="cmp-summary">
        <Stat num={comparison.total} label="Total Technologies" />
        <Stat num={comparison.shared_technologies.length} label="In Common" />
        <Stat num={comparison.only_in_a.length} label={`Unique to ${a.domain}`} />
        <Stat num={comparison.only_in_b.length} label={`Unique to ${b.domain}`} />
      </div>

      <div className="cmp-sites">
        <SiteCard site={a} />
        <SiteCard site={b} />
      </div>

      <div className="cmp-cols">
        <SharedColumn items={comparison.shared_technologies} a={a.domain} b={b.domain} />
        <UniqueColumn title={`Unique to ${a.domain}`} items={comparison.only_in_a} />
        <UniqueColumn title={`Unique to ${b.domain}`} items={comparison.only_in_b} />
      </div>

      <DiffOverview a={a} b={b} />
    </>
  );
}

function Stat({ num, label }) {
  return (
    <div className="card">
      <div className="stat__num">{num}</div>
      <div className="stat__label">{label}</div>
    </div>
  );
}

function SiteCard({ site }) {
  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> {site.domain}</h3>
      <div className="kv"><span className="kv__k">Technologies</span><span className="kv__v">{site.technologies.length}</span></div>
      <div className="kv"><span className="kv__k">Status</span><span className="kv__v">{site.status}</span></div>
      <div className="kv"><span className="kv__k">Analysed</span><span className="kv__v">{prettyDate(site.analyzed_at)}</span></div>
    </article>
  );
}

function SharedColumn({ items, a, b }) {
  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> In Common ({items.length})</h3>
      <p className="cmp-legend">Confidence: {a} / {b}</p>
      <div className="scroll">
        {items.length === 0 && <p className="muted">Without technologies in common.</p>}
        {items.map((t) => (
          <div className="tech" key={t.name}>
            <div>
              <div className="tech__name">{t.name}</div>
              <div className="tech__cat">{t.category}</div>
            </div>
            <div className="tech__confs">
              <span className={"tech__conf " + confClass(t.confidence_a)}>{t.confidence_a}%</span>
              <span className={"tech__conf " + confClass(t.confidence_b)}>{t.confidence_b}%</span>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

function UniqueColumn({ title, items }) {
  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> {title} ({items.length})</h3>
      <div className="scroll">
        {items.length === 0 && <p className="muted">None.</p>}
        {items.map((t) => (
          <div className="tech" key={t.name}>
            <div>
              <div className="tech__name">{t.name}</div>
              <div className="tech__cat">{t.category}</div>
            </div>
            <span className={"tech__conf " + confClass(t.confidence)}>{t.confidence}%</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function DiffOverview({ a, b }) {
  const ca = countByCategory(a.technologies);
  const cb = countByCategory(b.technologies);
  return (
    <article className="card span-3">
      <h3 className="card__title"><span className="dot" /> Differences Overview</h3>
      <div className="diff">
        {CATEGORIES.map((cat) => (
          <div className="diff__row" key={cat}>
            <span className="diff__a">{ca[cat] || 0}</span>
            <span className="diff__cat">{cat}</span>
            <span className="diff__b">{cb[cat] || 0}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function countByCategory(techs = []) {
  const counts = {};
  for (const t of techs) counts[t.category] = (counts[t.category] || 0) + 1;
  return counts;
}
