import { useState } from "react";
import { call, API_BASE } from "../api";

// Probador crudo de la API (herramienta de desarrollo). Mantiene estilos inline
// a propósito: NO es parte del diseño de producto, solo un harness de pruebas.
const TABS = [
  {
    key: "analyze",
    label: "Analyze",
    fields: [{ name: "url", placeholder: "github.com" }],
    run: (v) => call("/analyses/", { method: "POST", body: JSON.stringify({ url: v.url }) }),
  },
  {
    key: "snapshot",
    label: "Snapshot",
    fields: [{ name: "snapshot_url", placeholder: "https://web.archive.org/web/2023.../https://github.com/" }],
    run: (v) => call("/analyses/snapshot/", { method: "POST", body: JSON.stringify({ snapshot_url: v.snapshot_url }) }),
  },
  {
    key: "historical",
    label: "Historical",
    fields: [{ name: "url", placeholder: "github.com (analiza ~12 capturas, es lento)" }],
    run: (v) => call("/analyses/historical/", { method: "POST", body: JSON.stringify({ url: v.url }) }),
  },
  {
    key: "list",
    label: "List",
    fields: [],
    run: () => call("/analyses/"),
  },
  {
    key: "detail",
    label: "Detail",
    fields: [{ name: "id", placeholder: "1 (id del análisis)" }],
    run: (v) => call(`/analyses/${v.id}/`),
  },
  {
    key: "compare",
    label: "Compare",
    fields: [
      { name: "url_a", placeholder: "github.com" },
      { name: "url_b", placeholder: "vercel.com" },
    ],
    run: (v) => call("/analyses/compare/", { method: "POST", body: JSON.stringify({ url_a: v.url_a, url_b: v.url_b }) }),
  },
  {
    key: "history",
    label: "History",
    fields: [{ name: "domain", placeholder: "github.com (dominio)" }],
    run: (v) => call(`/domains/${v.domain}/analyses/`),
  },
  {
    key: "stats",
    label: "Stats",
    fields: [],
    run: () => call("/stats/"),
  },
];

export default function ApiTesterView() {
  const [activeKey, setActiveKey] = useState(TABS[0].key);
  const [values, setValues] = useState({});
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  const tab = TABS.find((t) => t.key === activeKey);

  function switchTab(key) {
    setActiveKey(key);
    setValues({});
    setOutput("");
  }

  async function handleGo() {
    setLoading(true);
    setOutput("Loading…");
    try {
      const result = await tab.run(values);
      setOutput(JSON.stringify(result, null, 2));
    } catch (err) {
      setOutput(
        "Request failed: " + err.message +
        "\n\n¿El backend está corriendo en :8000? ¿Aplicaste CORS?"
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <h1 style={{ margin: 0, color: "#e7eaf2" }}>API Tester</h1>
      <p style={styles.base}>Base URL: {API_BASE}</p>

      <div style={styles.tabs}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => switchTab(t.key)}
            style={{
              ...styles.tab,
              background: t.key === activeKey ? "#2563eb" : "#e5e7eb",
              color: t.key === activeKey ? "#fff" : "#111",
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div style={styles.form}>
        {tab.fields.length === 0 && (
          <p style={{ color: "#8a93a8", margin: "0 0 8px" }}>Este endpoint no necesita parámetros.</p>
        )}
        {tab.fields.map((f) => (
          <input
            key={f.name}
            placeholder={f.placeholder}
            value={values[f.name] || ""}
            onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
            onKeyDown={(e) => e.key === "Enter" && handleGo()}
            style={styles.input}
          />
        ))}
        <button onClick={handleGo} disabled={loading} style={styles.go}>
          {loading ? "…" : "Go"}
        </button>
      </div>

      <pre style={styles.output}>{output || "— sin resultado todavía —"}</pre>
    </div>
  );
}

const styles = {
  page: { fontFamily: "system-ui, sans-serif", maxWidth: 900 },
  base: { color: "#8a93a8", marginTop: 4 },
  tabs: { display: "flex", gap: 8, flexWrap: "wrap", margin: "16px 0" },
  tab: { padding: "8px 14px", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 14 },
  form: { marginBottom: 16 },
  input: { display: "block", width: "100%", padding: 8, marginBottom: 8, boxSizing: "border-box", fontSize: 14 },
  go: { padding: "10px 28px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 15 },
  output: { background: "#0b0e14", color: "#d1d5db", padding: 16, borderRadius: 8, overflow: "auto", maxHeight: 520, fontSize: 13, lineHeight: 1.5 },
};
