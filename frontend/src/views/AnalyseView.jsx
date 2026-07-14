import { useState } from "react";
import AiChatPanel from "../components/AiChatPanel";
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
  if (!data) return <div className="placeholder">Write an URL above and press Enter to analyse.</div>;

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
        <DnsCard dns={dns} email={data.email_security} rdns={geo?.reverse_dns} />
        <DomainDetailsCard whois={whois} tls={data.tls} />
        <TechnologiesCard technologies={technologies} security={data.security} />
        <GeoCard geo={geo} />
        <SummaryCard technologies={technologies} security={data.security} />
        <SnapshotsCard wayback={wayback} onRetry={onRetryWayback} onViewHistorical={onViewHistorical} />
      </div>

      {/* El wayback se carga aparte (App.jsx) y no viene dentro de `data`: se
          inyecta aquí para que la IA vea el mismo historial que la tarjeta. */}
      <AiChatPanel analysis={wayback?.data ? { ...data, wayback: wayback.data } : data} />
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

// Registros DNS "cortos" mostrados en orden; los tipos sin registros se ocultan.
// TXT se trata aparte (colapsable) porque suele traer decenas de registros largos.
const DNS_TYPES = ["A", "AAAA", "CNAME", "NS", "MX"];

// Chip compacto de estado (SPF, DMARC, DNSSEC): verde ✓ presente / gris ✗ ausente.
function EmailChip({ ok, label, title }) {
  return (
    <span className={"echip " + (ok ? "echip--ok" : "echip--bad")} title={title || ""}>
      {ok ? "✓" : "✗"} {label}
    </span>
  );
}

// Política del registro DMARC para el chip: "…p=reject…" → "reject".
function dmarcPolicy(dmarc) {
  const m = (dmarc || "").match(/p=(\w+)/i);
  return m ? m[1] : null;
}

function DnsCard({ dns, email, rdns }) {
  const [showTxt, setShowTxt] = useState(false);
  if (!dns) return <Card title="DNS"><p className="muted">No DNS data.</p></Card>;

  const groups = DNS_TYPES
    .map((type) => [type, dns[type] || []])
    .filter(([, vals]) => vals.length > 0);
  const txt = dns.TXT || [];

  if (groups.length === 0 && txt.length === 0 && !rdns && !email) {
    return <Card title="DNS"><p className="muted">No DNS records.</p></Card>;
  }

  return (
    <Card title="DNS">
      <div className="scroll">
      {groups.map(([type, vals]) => (
        <Row
          key={type}
          k={type}
          v={
            <div className="dns-vals">
              {vals.map((val, i) => (
                <span className="mono dns-vals__item" key={i}>{val}</span>
              ))}
            </div>
          }
        />
      ))}

      {rdns && <Row k="PTR" v={<span className="mono">{rdns}</span>} />}

      {/* TXT colapsado: por defecto solo el conteo; se expande en caja con scroll */}
      {txt.length > 0 && (
        <>
          <div className="kv">
            <span className="kv__k">TXT</span>
            <button className="dns-txt__toggle" onClick={() => setShowTxt((v) => !v)}>
              {txt.length} record{txt.length !== 1 ? "s" : ""} {showTxt ? "▾" : "▸"}
            </button>
          </div>
          {showTxt && (
            <div className="dns-txt__box">
              {txt.map((val, i) => (
                <div className="dns-txt__item mono" key={i} title={val}>{val}</div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Email / DNS security: SPF, DMARC, DNSSEC en una sola fila de chips */}
      {email && (
        <>
          <div className="dd-subhead">Email Security</div>
          <div className="echips">
            <EmailChip ok={!!email.spf} label="SPF" title={email.spf} />
            <EmailChip
              ok={!!email.dmarc}
              label={dmarcPolicy(email.dmarc) ? `DMARC · ${dmarcPolicy(email.dmarc)}` : "DMARC"}
              title={email.dmarc}
            />
            <EmailChip ok={email.dnssec} label="DNSSEC" />
          </div>
        </>
      )}
      </div>
    </Card>
  );
}

// Fila que se OCULTA si el valor está vacío (consistente con la decisión de UI).
function OptRow({ k, v }) {
  if (v == null || v === "" || (Array.isArray(v) && v.length === 0)) return null;
  return <Row k={k} v={v} />;
}

// Días desde hoy hasta una fecha ISO (negativo si ya pasó). Para cuentas regresivas.
function daysUntil(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d) ? null : Math.round((d - Date.now()) / 86400000);
}

function DateWithCountdown({ iso }) {
  const days = daysUntil(iso);
  return (
    <span>
      {prettyDate(iso)}
      {days != null && <span className="muted"> · {days < 0 ? "expired" : `in ${days}d`}</span>}
    </span>
  );
}

// "WHOIS" ampliado: datos de registro del dominio + reverse DNS + certificado SSL.
function DomainDetailsCard({ whois, tls }) {
  const w = whois || {};
  const hasWhois = whois && Object.values(w).some((x) => x != null && x !== "" && !(Array.isArray(x) && !x.length));
  if (!hasWhois && !tls) {
    return <Card title="Domain Details"><p className="muted">No domain data.</p></Card>;
  }

  // Códigos EPP de estado: "clientDeleteProhibited https://…" → "clientDeleteProhibited".
  const statusCodes = (w.status || []).map((s) => String(s).split(/\s+/)[0]).filter(Boolean);

  return (
    <Card title="WHOIS (Domain Details)">
      <div className="scroll">
        <OptRow k="Registrar" v={w.registrar} />
        <OptRow k="Organization" v={w.org || w.registrant} />
        <OptRow k="Country" v={w.country} />
        <OptRow k="Created" v={w.creation_date ? prettyDate(w.creation_date) : null} />
        <OptRow k="Updated" v={w.updated_date ? prettyDate(w.updated_date) : null} />
        <OptRow k="Expires" v={w.expiration_date ? <DateWithCountdown iso={w.expiration_date} /> : null} />
        <OptRow k="Age" v={w.domain_age_years != null ? w.domain_age_years + " years" : null} />
        <OptRow k="Status" v={statusCodes.length ? <span className="mono dd-status">{statusCodes.join(", ")}</span> : null} />

        {tls && <TlsSection tls={tls} />}
      </div>
    </Card>
  );
}

function TlsSection({ tls }) {
  const [open, setOpen] = useState(false);
  if (tls.valid === false) {
    return (
      <>
        <div className="dd-subhead">SSL Certificate</div>
        <OptRow k="Status" v={<span className="conf--low tls-bad">Invalid certificate</span>} />
        <OptRow k="Reason" v={tls.error ? <span className="muted">{tls.error}</span> : null} />
      </>
    );
  }
  const sans = tls.san || [];
  const days = tls.days_to_expiry;
  // Nombre que cubre el cert para el resumen: el Common Name si existe; si no
  // (certs modernos sin CN), el SAN wildcard *.dominio.tld, o el primer SAN.
  const wildcard = sans.find((s) => s.startsWith("*."));
  const certName = tls.subject_cn || wildcard || sans[0] || null;
  const summary = [certName, days != null ? (days < 0 ? "expired" : `${days}d left`) : null]
    .filter(Boolean).join(" · ");
  return (
    <>
      <button className="dd-subhead-toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className="dd-toggle-label">SSL Certificate</span>
        <span className="dd-summary">{summary}</span>
        <span className="dd-chevron">{open ? "▾" : "▸"}</span>
      </button>
      {open && (
        <>
          <OptRow k="Issuer" v={tls.issuer} />
          <OptRow k="Common name" v={tls.subject_cn ? <span className="mono">{tls.subject_cn}</span> : null} />
          <OptRow k="Valid until" v={tls.valid_to ? <DateWithCountdown iso={tls.valid_to} /> : null} />
          <OptRow k="TLS version" v={tls.tls_version} />
          <OptRow k="Domains (SAN)" v={sans.length ? <span title={sans.join(", ")}>{sans.length}</span> : null} />
        </>
      )}
    </>
  );
}

// "HTML contiene 'x'; script src contiene 'y'" → ["HTML contiene 'x'", ...]
function splitEvidence(evidence) {
  return (evidence || "").split(";").map((e) => e.trim()).filter(Boolean);
}

function TechnologiesCard({ technologies, security }) {
  // openName: evidencia abierta al hacer click en una tecnología (una a la vez).
  // expandAll: muestra TODAS las evidencias inline. La tarjeta NO crece: el
  //            contenido desborda dentro de .scroll (alto fijo) y hace scroll
  //            interno, así la grilla (DNS/WHOIS) no se deforma.
  const [openName, setOpenName] = useState(null);
  const [expandAll, setExpandAll] = useState(false);
  // Nombres de tecnologías marcadas End-of-Life por la auditoría de seguridad.
  const eolNames = new Set(
    (security?.findings || []).filter((f) => f.category === "outdated").map((f) => f.tech)
  );

  return (
    <Card title={`Technologies (${technologies.length})`}>
      {technologies.length > 0 && (
        <button
          className="tech-expand"
          onClick={() => { setExpandAll((v) => !v); setOpenName(null); }}
        >
          {expandAll ? "▾ Collapse evidence" : "▸ Show all evidence"}
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
                    {eolNames.has(t.name) && <span className="tech__eol" title="End-of-Life: unsupported version">EOL</span>}
                  </div>
                  <div className="tech__cat">{t.category}</div>
                </div>
                <span className={"tech__conf " + confClass(t.confidence)}>{t.confidence}%</span>
              </button>
              {open && (
                <div className="tech__evidence">
                  <div className="tech__evidence-title">Evidences</div>
                  {items.length ? (
                    <ul>{items.map((e, i) => <li key={i}>{e}</li>)}</ul>
                  ) : (
                    <span className="muted">No evidence registred.</span>
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

function SummaryCard({ technologies, security }) {
  const [showFindings, setShowFindings] = useState(false);
  const findings = security?.findings || [];
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

      {security && (
        <div className="sec">
          <div className="sec__head">
            <span className={"sec__grade sec__grade--" + security.grade}>{security.grade}</span>
            <div>
              <div className="sec__title-lbl">Security grade</div>
              <div className="sec__sub">{findings.length} issue{findings.length !== 1 ? "s" : ""} found</div>
            </div>
            {findings.length > 0 && (
              <button className="sec__toggle" onClick={() => setShowFindings((v) => !v)}>
                {showFindings ? "Hide" : "Details"}
              </button>
            )}
          </div>
          {showFindings && (
            <ul className="sec__list">
              {findings.map((f, i) => (
                <li key={i} className={"sec__item sec__item--" + f.severity}>
                  <span className="sec__sev">{f.severity}</span>
                  <span className="sec__ftitle" title={f.detail}>{f.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
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
          See all snapshots with its technologies ↗
        </button>
      )}
      {wayback?.status === "failed" && (
        <div className="snap-fail">
          <span className="muted">Could not load the snapshots.</span>
          <button className="retry-btn" onClick={onRetry}>Retry</button>
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
