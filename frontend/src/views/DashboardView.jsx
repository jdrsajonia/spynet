import { useState } from "react";
import Donut from "../components/charts/Donut";
import Ring from "../components/charts/Ring";
import LineChart from "../components/charts/LineChart";
import { prettyDate } from "../utils/format";
import { CATEGORIES } from "../utils/categories";

// Vista Dashboard. Presentacional: recibe {data:{stats,recent}, loading, error}.
// Todo lo que pinta sale de datos reales del backend (/stats/ + /analyses/).

export default function DashboardView({ data, loading, error }) {
  if (loading) return <div className="placeholder">Cargando dashboard…</div>;
  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="placeholder">Sin datos.</div>;

  const { stats, recent } = data;

  return (
    <section>
      <header className="dash-head">
        <div>
          <h2 className="dash-head__title">Dashboard</h2>
          <p className="dash-head__sub">Resumen de todos los análisis y tendencias detectadas por Spynet.</p>
        </div>
        <span className="dash-chip">All time</span>
      </header>

      <div className="dash-kpis">
        <Kpi label="Total Analyses"      num={stats.total_analyses} />
        <Kpi label="Unique Domains"      num={stats.unique_domains} />
        <Kpi label="Total Detections"    num={stats.total_detections} />
        <Kpi label="Avg Analysis Time"   num={stats.avg_analysis_time_seconds != null ? stats.avg_analysis_time_seconds + "s" : "—"} />
      </div>

      <div className="dash-tables">
        <TopTechnologies items={stats.top_technologies} />
        <RecentlyAnalysed rows={recent} />
      </div>

      <div className="dash-charts">
        <CategoryDonut byCategory={stats.by_category} total={stats.total_detections} />
        <Confidence value={Math.round(stats.avg_confidence || 0)} />
        <Activity activity={stats.activity} />
      </div>
    </section>
  );
}

function Kpi({ label, num }) {
  return (
    <article className="card kpi">
      <div>
        <div className="kpi__label">{label}</div>
        <div className="kpi__num">{num}</div>
      </div>
      <div className="kpi__icon">▦</div>
    </article>
  );
}

function TopTechnologies({ items }) {
  const [cat, setCat] = useState("all");
  const filtered = (cat === "all" ? items : items.filter((t) => t.category === cat)).slice(0, 6);
  const max = Math.max(...filtered.map((t) => t.count), 1);

  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> Top Technologies</h3>
      <div className="filter-tabs">
        {["all", "frontend", "backend", "cdn", "server", "analytics"].map((c) => (
          <button key={c} className={cat === c ? "is-active" : ""} onClick={() => setCat(c)}>
            {c === "all" ? "All" : c[0].toUpperCase() + c.slice(1)}
          </button>
        ))}
      </div>
      {filtered.length === 0 && <p className="muted">Sin datos en esta categoría.</p>}
      {filtered.map((t, i) => (
        <div className="rank" key={t.name + t.category}>
          <span className="rank__pos">{i + 1}</span>
          <span className="rank__name">{t.name}</span>
          <div className="rank__bar"><div className="rank__fill" style={{ width: (t.count / max) * 100 + "%" }} /></div>
          <span className="rank__count">{t.count}</span>
        </div>
      ))}
    </article>
  );
}

function RecentlyAnalysed({ rows }) {
  return (
    <article className="card">
      <h3 className="card__title">
        <span className="dot" /> Recently Analysed Domains
        <span className="rad__count">{rows.length}</span>
      </h3>
      <div className="rad">
        <div className="rad__row rad__head">
          <span>Domain</span><span>Technologies</span><span>Date</span><span>Status</span>
        </div>
        {rows.length === 0 && <p className="muted">Aún no hay análisis.</p>}
        <div className="rad__body">
          {rows.map((a) => (
            <div className="rad__row" key={a.id}>
              <span className="rad__domain">{a.domain}</span>
              <span className="rad__techs">{a.technologies_count} techs</span>
              <span className="rad__date">{prettyDate(a.analyzed_at)}</span>
              <span className={"badge " + (a.status === "completed" ? "badge--ok" : "badge--partial")}>{a.status}</span>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}

function CategoryDonut({ byCategory, total }) {
  const segments = CATEGORIES.map((c) => ({ label: c.label, value: byCategory?.[c.key] || 0, color: c.color }));
  const sum = segments.reduce((s, x) => s + x.value, 0) || 1;
  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> Technologies by Category</h3>
      <div className="chart-center">
        <Donut segments={segments} total={total} />
        <div className="legend">
          {segments.map((s) => (
            <div className="legend__item" key={s.label}>
              <span className="legend__dot" style={{ background: s.color }} />
              {s.label}
              <span className="legend__val">{s.value} ({Math.round((s.value / sum) * 100)}%)</span>
            </div>
          ))}
        </div>
      </div>
    </article>
  );
}

function Confidence({ value }) {
  return (
    <article className="card confidence">
      <h3 className="card__title"><span className="dot" /> Avg Confidence</h3>
      <Ring value={value} />
    </article>
  );
}

function Activity({ activity = [] }) {
  const points = activity.slice(-30).map((a) => ({ label: a.date, value: a.count }));
  const sub = activityStats(activity);
  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> Activity Overview</h3>
      <LineChart points={points} />
      <div className="activity-sub">
        <div className="stat"><div className="stat__num">{sub.today}</div><div className="stat__label">Today</div></div>
        <div className="stat"><div className="stat__num">{sub.week}</div><div className="stat__label">This Week</div></div>
        <div className="stat"><div className="stat__num">{sub.month}</div><div className="stat__label">This Month</div></div>
      </div>
    </article>
  );
}

function activityStats(activity) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dayMs = 86400000;
  let t = 0, w = 0, m = 0;
  for (const a of activity) {
    const d = new Date(a.date + "T00:00:00");
    const diff = Math.floor((today - d) / dayMs);
    if (diff === 0) t += a.count;
    if (diff >= 0 && diff < 7) w += a.count;
    if (diff >= 0 && diff < 30) m += a.count;
  }
  return { today: t, week: w, month: m };
}
