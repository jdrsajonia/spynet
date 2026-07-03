import { useState } from "react";
import MapEmbed from "../components/MapEmbed";
import Scanning from "../components/Scanning";
import { confClass, yearOf, prettyDate, avgConfidence, seconds, snapshotThumbUrl } from "../utils/format";
import { categoryColor } from "../utils/categories";

// Vista "Analysis Results" (primer mockup). Componente presentacional: recibe
// {data, loading, error} y pinta los paneles. Cero estilos inline — todo en
// analyse.css. Se omiten Security Grade, Risk Level y el panel de IA (datos que
// el backend no produce hoy).
export default function AnalyseView({ data, loading, error, wayback, onRetryWayback, onViewHistorical }) {
  if (loading) return <Scanning />;
  if (error) return <div className="error">{error}</div>;
  if (!data) return <div className="placeholder">Escribe una URL arriba y presiona Enter para analizar.</div>;

  const { dns, whois, geo, technologies = [] } = data;

  return (
    <section>
      <header className="view-head">
        <h2 className="view-head__title">
          Analysis Results
          <span className={"badge " + (data.status === "completed" ? "badge--ok" : "badge--partial")}>
            {data.status}
          </span>
        </h2>
        <p className="view-head__url">{data.url}</p>
        <p className="view-head__meta">
          Analysed on {prettyDate(data.analyzed_at)} · completed in {seconds(data.duration_ms)}
        </p>
      </header>

      <div className="grid">
        <DnsCard dns={dns} />
        <WhoisCard whois={whois} />
        <TechnologiesCard technologies={technologies} />
        <GeoCard geo={geo} />
        <SummaryCard technologies={technologies} />
        <SnapshotsCard wayback={wayback} onRetry={onRetryWayback} onViewHistorical={onViewHistorical} />
      </div>
    </section>
  );
}

function Card({ title, span, children }) {
  return (
    <article className={"card" + (span ? " span-" + span : "")}>
      <h3 className="card__title"><span className="dot" /> {title}</h3>
      {children}
    </article>
  );
}

function Row({ k, v }) {
  return (
    <div className="kv">
      <span className="kv__k">{k}</span>
      <span className="kv__v">{v ?? "—"}</span>
    </div>
  );
}

function DnsCard({ dns }) {
  if (!dns) return <Card title="DNS"><p className="muted">No DNS data.</p></Card>;
  // Todas las IPs: A (IPv4) + AAAA (IPv6) si las hay, cada una en su propia fila
  // etiquetada IP A, IP B, IP C…
  const ips = [...(dns.A || []), ...(dns.AAAA || [])];
  return (
    <Card title="DNS">
      {ips.length === 0 && <Row k="IP" v="—" />}
      {ips.map((ip, i) => (
        <Row key={ip} k={`IP ${String.fromCharCode(65 + i)}`} v={<span className="mono">{ip}</span>} />
      ))}
      <Row k="Nameservers" v={<span className="mono">{(dns.NS || []).slice(0, 2).join(", ") || "—"}</span>} />
      <Row k="MX" v={<span className="mono">{(dns.MX || [])[0] || "—"}</span>} />
    </Card>
  );
}

function WhoisCard({ whois }) {
  if (!whois) return <Card title="WHOIS"><p className="muted">No WHOIS data.</p></Card>;
  return (
    <Card title="WHOIS">
      <Row k="Registrar" v={whois.registrar} />
      <Row k="Created" v={whois.creation_date ? prettyDate(whois.creation_date) : "—"} />
      <Row k="Expires" v={whois.expiration_date ? prettyDate(whois.expiration_date) : "—"} />
      <Row k="Age" v={whois.domain_age_years != null ? whois.domain_age_years + " years" : "—"} />
    </Card>
  );
}

// "HTML contiene 'x'; script src contiene 'y'" → ["HTML contiene 'x'", ...]
function splitEvidence(evidence) {
  return (evidence || "").split(";").map((e) => e.trim()).filter(Boolean);
}

function TechnologiesCard({ technologies }) {
  // openName: evidencia abierta al hacer click en una tecnología (una a la vez).
  // expandAll: muestra TODAS las evidencias inline. La tarjeta NO crece: el
  //            contenido desborda dentro de .scroll (alto fijo) y hace scroll
  //            interno, así la grilla (DNS/WHOIS) no se deforma.
  const [openName, setOpenName] = useState(null);
  const [expandAll, setExpandAll] = useState(false);

  return (
    <Card title={`Technologies (${technologies.length})`}>
      {technologies.length > 0 && (
        <button
          className="tech-expand"
          onClick={() => { setExpandAll((v) => !v); setOpenName(null); }}
        >
          {expandAll ? "▾ Colapsar evidencias" : "▸ Ver todas las evidencias"}
        </button>
      )}
      <div className="scroll">
        {technologies.length === 0 && <p className="muted">No technologies detected.</p>}
        {technologies.map((t) => {
          const open = expandAll || openName === t.name;
          const items = splitEvidence(t.evidence);
          return (
            <div className="tech-item" key={t.name}>
              <button
                type="button"
                className={"tech" + (open ? " is-open" : "")}
                onClick={() => { if (!expandAll) setOpenName(openName === t.name ? null : t.name); }}
                aria-expanded={open}
              >
                <span className="tech__dot" style={{ background: categoryColor(t.category) }} />
                <div className="tech__meta">
                  <div className="tech__name">
                    {t.name}
                    {t.version && <span className="tech__ver">v{t.version}</span>}
                  </div>
                  <div className="tech__cat">{t.category}</div>
                </div>
                <span className={"tech__conf " + confClass(t.confidence)}>{t.confidence}%</span>
              </button>
              {open && (
                <div className="tech__evidence">
                  <div className="tech__evidence-title">Evidencias</div>
                  {items.length ? (
                    <ul>{items.map((e, i) => <li key={i}>{e}</li>)}</ul>
                  ) : (
                    <span className="muted">Sin evidencia registrada.</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function GeoCard({ geo }) {
  if (!geo) return <Card title="Geolocation" span={2}><p className="muted">No geolocation data.</p></Card>;
  return (
    <Card title="Geolocation" span={2}>
      <div className="geo">
        <div>
          <Row k="Country" v={geo.country} />
          <Row k="City" v={geo.city} />
          <Row k="ISP" v={geo.isp} />
          <Row k="Organization" v={geo.org} />
          <Row k="IP" v={<span className="mono">{geo.ip}</span>} />
          <Row k="Coordinates" v={geo.lat != null ? `${geo.lat}, ${geo.lon}` : "—"} />
        </div>
        <MapEmbed lat={geo.lat} lon={geo.lon} />
      </div>
    </Card>
  );
}

function SummaryCard({ technologies }) {
  return (
    <Card title="Summary">
      <div className="summary">
        <div className="stat">
          <div className="stat__num">{technologies.length}</div>
          <div className="stat__label">Technologies</div>
        </div>
        <div className="stat">
          <div className="stat__num">{avgConfidence(technologies)}%</div>
          <div className="stat__label">Avg confidence</div>
        </div>
      </div>
    </Card>
  );
}

function SnapshotsCard({ wayback, onRetry, onViewHistorical }) {
  const snapshots = wayback?.data?.snapshots ?? [];
  return (
    <Card title="Snapshots (Wayback Machine)" span={3}>
      {wayback?.status === "idle" && <p className="muted">—</p>}
      {wayback?.status === "loading" && (
        <Scanning text="Waiting for Wayback Machine results..." />
      )}
      {wayback?.status === "done" && snapshots.length > 0 && (
        <button className="hist-cta" onClick={onViewHistorical}>
          Ver todas las snapshots con sus tecnologías ↗
        </button>
      )}
      {wayback?.status === "failed" && (
        <div className="snap-fail">
          <span className="muted">No se pudieron cargar los snapshots.</span>
          <button className="retry-btn" onClick={onRetry}>Reintentar</button>
        </div>
      )}
      {wayback?.status === "done" && (
        <div className="timeline">
          {snapshots.map((s) => (
            <div className="snap" key={s.timestamp}>
              <div className="snap__thumb">
                <iframe
                  title={`snapshot ${s.timestamp}`}
                  src={snapshotThumbUrl(s.url, s.timestamp)}
                  loading="lazy"
                  scrolling="no"
                />
              </div>
              <div className="snap__year">{yearOf(s.timestamp)}</div>
              <div className="snap__date">{s.timestamp.slice(0, 8)}</div>
              <a href={s.url} target="_blank" rel="noreferrer">View ↗</a>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}
