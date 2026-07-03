import { useState } from "react";
import Scanning from "../components/Scanning";
import { confClass, snapshotThumbUrl } from "../utils/format";
import { categoryColor } from "../utils/categories";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Vista Historical (mockup 2). Presentacional: recibe {url, data, loading, error}
// y una acción onAnalyze(url). NO hace análisis en vivo: solo Wayback, analizando
// las tecnologías de CADA captura archivada (frontend/backend sobre el HTML).
//
// La respuesta del backend tiene dos formas:
//   · con historial  → data.wayback.snapshots[]
//   · sin historial  → data.snapshots === []  (respuesta vacía, 200)
export default function HistoricalView({ url, onUrlChange, onAnalyze, data, loading, error }) {
  const [local, setLocal] = useState(url || "");

  // Sincroniza el input cuando la URL llega desde fuera (forma 1: botón
  // "Ver todas las snapshots" en Analyse precarga la URL).
  if (url !== undefined && url !== local && document.activeElement?.name !== "hist-url") {
    setLocal(url);
  }

  function submit(e) {
    e.preventDefault();
    onUrlChange?.(local);
    onAnalyze(local);
  }

  const snapshots = data?.wayback?.snapshots ?? data?.snapshots ?? [];
  const ordered = [...snapshots].sort((a, b) => (b.timestamp || "").localeCompare(a.timestamp || ""));

  return (
    <section>
      <header className="hist-head">
        <div className="hist-head__intro">
          <h2 className="hist-head__title">Historical Analysis</h2>
          <p className="hist-head__sub">
            Explora cómo ha evolucionado un sitio en el tiempo.

          </p>
        </div>
        <form className="hist-head__form" onSubmit={submit}>
          <input
            name="hist-url"
            className="hist-head__input"
            placeholder="Escribe una URL para explorar su historial (ej. example.com)"
            value={local}
            onChange={(e) => setLocal(e.target.value)}
            autoComplete="off"
          />
          <button className="hist-head__btn" type="submit" disabled={loading || !local.trim()}>
            {loading ? "Buscando…" : "Explore History ›"}
          </button>
        </form>
      </header>

      {loading && <Scanning text="Scanning the web archives…" />}
      {error && <div className="error">{error}</div>}

      {!loading && !error && data && ordered.length === 0 && (
        <div className="placeholder">No hay capturas archivadas para este dominio.</div>
      )}
      {!loading && !error && !data && (
        <div className="placeholder">Escribe una URL y presiona «Explore History».</div>
      )}

      {!loading && ordered.length > 0 && (
        <>
          <div className="timeline-v">
            {ordered.map((s, i) => (
              <SnapshotRow key={s.timestamp + s.url} snap={s} latest={i === 0} />
            ))}
          </div>
          <p className="hist-count">
            ⓘ Mostrando {ordered.length} capturas del historial de Wayback Machine
          </p>
        </>
      )}
    </section>
  );
}

function SnapshotRow({ snap, latest }) {
  const techs = snap.technologies || [];
  return (
    <div className={"tl-item" + (latest ? " tl-item--latest" : "")}>
      <div className="tl-meta">
        <span className="tl-year">{(snap.timestamp || "").slice(0, 4) || "—"}</span>
        <span className="tl-date">{formatDate(snap.timestamp)}</span>
        <span className="tl-time">{formatTime(snap.timestamp)}</span>
      </div>
      <div className="tl-spine">
        <span className="tl-node" />
      </div>
      <article className="tl-card">
        <div className="tl-thumb">
          <iframe
            title={`snapshot ${snap.timestamp}`}
            src={snapshotThumbUrl(snap.url, snap.timestamp)}
            loading="lazy"
            scrolling="no"
          />
        </div>
        <div className="tl-body">
          <div className="tl-body__label">Detected Technologies</div>
          {techs.length === 0 ? (
            <p className="muted">No se detectaron tecnologías en esta captura.</p>
          ) : (
            <div className="tl-techs">
              {techs.map((t) => (
                <span className="tl-tech" key={t.name} title={`${t.category} · ${t.confidence}%`}>
                  <span className="tl-tech__dot" style={{ background: categoryColor(t.category) }} />
                  <span className="tl-tech__name">{t.name}</span>
                  {t.version && <span className="tech__ver">v{t.version}</span>}
                  <span className={"tl-tech__conf " + confClass(t.confidence)}>{t.confidence}%</span>
                </span>
              ))}
            </div>
          )}
        </div>
        <a className="tl-wayback" href={snap.url} target="_blank" rel="noreferrer">
          View on Wayback Machine ↗
        </a>
      </article>
    </div>
  );
}

// "20210518123456" → "May 18, 2021"
function formatDate(ts = "") {
  if (ts.length < 8) return ts;
  const m = parseInt(ts.slice(4, 6), 10);
  return `${MONTHS[m - 1] || "?"} ${ts.slice(6, 8)}, ${ts.slice(0, 4)}`;
}

// "20210518123456" → "12:34:56 UTC"
function formatTime(ts = "") {
  if (ts.length < 14) return "";
  return `${ts.slice(8, 10)}:${ts.slice(10, 12)}:${ts.slice(12, 14)} UTC`;
}
