import { useState, useEffect, useRef } from "react";

import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import { Icon } from "./components/icons";
import HomeView from "./views/HomeView";
import AnalyseView from "./views/AnalyseView";
import CompareView from "./views/CompareView";
import DashboardView from "./views/DashboardView";
import HistoricalView from "./views/HistoricalView";
import ApiDocsView from "./views/ApiDocsView";
import { call, fetchSchema } from "./api";

import "./styles/tokens.css";
import "./styles/layout.css";
import "./styles/home.css";
import "./styles/analyse.css";
import "./styles/compare.css";
import "./styles/dashboard.css";
import "./styles/historical.css";
import "./styles/apidocs.css";

// El contenedor: aquí vive el ESTADO y la LÓGICA (qué se pide al backend). Las
// vistas y el shell son presentacionales y solo reciben props. Esto mantiene la
// lógica separada de la presentación.
const NAV = [
  { key: "home",       label: "Home",       icon: Icon.home },
  { key: "analyse",    label: "Analyse",    icon: Icon.analyse },
  { key: "historical", label: "Historical", icon: Icon.historical },
  
  { key: "compare",    label: "Compare",    icon: Icon.compare },
  { key: "dashboard",  label: "Dashboard",  icon: Icon.dashboard },
  { key: "apidocs",    label: "API Docs",   icon: Icon.apidocs },
];

export default function App() {
  const [view, setView] = useState("home");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  // Carga diferida de Wayback. status: idle | loading | done | failed
  const [wayback, setWayback] = useState({ status: "idle", data: null });

  const [cmpData, setCmpData] = useState(null);
  const [cmpLoading, setCmpLoading] = useState(false);
  const [cmpError, setCmpError] = useState(null);

  const [dashData, setDashData] = useState(null);
  const [dashLoading, setDashLoading] = useState(false);
  const [dashError, setDashError] = useState(null);

  // Documento OpenAPI que describe la API. Se pide una sola vez y se queda en
  // memoria: no cambia mientras el backend no se reinicie.
  const [schema, setSchema] = useState(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [schemaError, setSchemaError] = useState(null);

  // Historical: análisis pasivo de todas las capturas de Wayback (solo tecnologías).
  const [histUrl, setHistUrl] = useState("");
  const [histData, setHistData] = useState(null);
  const [histLoading, setHistLoading] = useState(false);
  const [histError, setHistError] = useState(null);
  // Caché por URL: el análisis histórico es caro (descarga ~12 páginas
  // archivadas). Una vez computado para una URL, reingresar o volver a pulsar
  // "Ver todas las snapshots" lo muestra al instante, sin volver a llamar la API.
  const histCache = useRef({});

  // El dashboard es de solo lectura: se carga al entrar a la pestaña.
  useEffect(() => {
    if (view !== "dashboard" || dashData || dashLoading) return;
    (async () => {
      setDashLoading(true);
      setDashError(null);
      try {
        const [statsRes, listRes] = await Promise.all([
          call("/stats/"),
          call("/analyses/?page_size=100"),
        ]);
        if (statsRes.body.success && listRes.body.success) {
          setDashData({ stats: statsRes.body.data, recent: listRes.body.data });
        } else {
          setDashError("Failed to load the dashboard.");
        }
      } catch {
        setDashError("Couldn't reach the backend (is it running on :8000?).");
      } finally {
        setDashLoading(false);
      }
    })();
  }, [view, dashData, dashLoading]);

  // Igual que el dashboard: se carga al entrar a la pestaña, no al arrancar.
  useEffect(() => {
    if (view !== "apidocs" || schema || schemaLoading) return;
    (async () => {
      setSchemaLoading(true);
      setSchemaError(null);
      try {
        setSchema(await fetchSchema());
      } catch {
        setSchemaError("Couldn't load the schema (is the backend running on :8000?).");
      } finally {
        setSchemaLoading(false);
      }
    })();
  }, [view, schema, schemaLoading]);

  async function runAnalyze(url) {
    if (!url.trim()) return;
    setView("analyse");
    setLoading(true);
    setError(null);
    setData(null);
    setWayback({ status: "idle", data: null });
    try {
      const { status, body } = await call("/analyses/", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      if (body.success) {
        setData(body.data);
        loadWayback(body.data.id);   // en segundo plano, sin bloquear
      } else {
        setError(body.error?.message || `Error ${status}`);
      }
    } catch {
      setError("Couldn't reach the backend (is it running on :8000?).");
    } finally {
      setLoading(false);
    }
  }

  // Pide Wayback aparte. Reintenta solo hasta 3 veces (Wayback suele estar lento);
  // si tras eso no aparece, queda en "failed" y el usuario puede reintentar a mano.
  async function loadWayback(id, attempt = 1) {
    setWayback({ status: "loading", data: null });
    try {
      const { body } = await call(`/analyses/${id}/wayback/`, { method: "POST" });
      if (body.success && body.data && body.data.snapshots?.length) {
        setWayback({ status: "done", data: body.data });
      } else if (attempt < 3) {
        setTimeout(() => loadWayback(id, attempt + 1), 2500);
      } else {
        setWayback({ status: "failed", data: null });
      }
    } catch {
      if (attempt < 3) setTimeout(() => loadWayback(id, attempt + 1), 2500);
      else setWayback({ status: "failed", data: null });
    }
  }

  // Historical: solo Wayback, analizando las tecnologías de cada captura. Es
  // pesado (descarga ~12 páginas archivadas), por eso el pingüino cubre la espera.
  // Si ya se computó para esta URL, sale del caché sin tocar la API.
  async function runHistorical(url) {
    const key = url.trim().toLowerCase();
    if (!key) return;

    const cached = histCache.current[key];
    if (cached) {
      setHistError(null);
      setHistLoading(false);
      setHistData(cached);
      return;
    }

    setHistLoading(true);
    setHistError(null);
    setHistData(null);
    try {
      const { status, body } = await call("/analyses/historical/", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      if (body.success) {
        histCache.current[key] = body.data;
        setHistData(body.data);
      } else {
        setHistError(body.error?.message || `Error ${status}`);
      }
    } catch {
      setHistError("Couldn't reach the backend (is it running on :8000?).");
    } finally {
      setHistLoading(false);
    }
  }

  // Forma 1: desde Analyse, "Ver todas las snapshots" salta a Historical con la
  // URL precargada y dispara el análisis histórico automáticamente.
  function viewHistorical(url) {
    setView("historical");
    setHistUrl(url);
    runHistorical(url);
  }

  async function runCompare(urlA, urlB) {
    if (!urlA.trim() || !urlB.trim()) return;
    setCmpLoading(true);
    setCmpError(null);
    setCmpData(null);
    try {
      const { status, body } = await call("/analyses/compare/", {
        method: "POST",
        body: JSON.stringify({ url_a: urlA, url_b: urlB }),
      });
      if (body.success) setCmpData(body.data);
      else setCmpError(body.error?.message || `Error ${status}`);
    } catch {
      setCmpError("Couldn't reach the backend (is it running on :8000?).");
    } finally {
      setCmpLoading(false);
    }
  }

  return (
    <div className="app">
      <Sidebar items={NAV} active={view} onSelect={setView} />
      <div>
        <Topbar onSearch={runAnalyze} busy={loading} showSearch={view !== "historical"} />
        <main className="content">
          {view === "home" && <HomeView />}
          {view === "analyse" && (
            <AnalyseView
              data={data}
              loading={loading}
              error={error}
              wayback={wayback}
              onRetryWayback={() => data?.id && loadWayback(data.id)}
              onViewHistorical={() => data?.url && viewHistorical(data.url)}
            />
          )}
          {view === "historical" && (
            <HistoricalView
              url={histUrl}
              onUrlChange={setHistUrl}
              onAnalyze={runHistorical}
              data={histData}
              loading={histLoading}
              error={histError}
            />
          )}
          {view === "compare" && (
            <CompareView data={cmpData} loading={cmpLoading} error={cmpError} onCompare={runCompare} />
          )}
          {view === "dashboard" && (
            <DashboardView data={dashData} loading={dashLoading} error={dashError} />
          )}
          {view === "apidocs" && (
            <ApiDocsView schema={schema} loading={schemaLoading} error={schemaError} />
          )}
          {!["home", "analyse", "historical", "compare", "dashboard", "apidocs"].includes(view) && (
            <div className="placeholder">— vista «{view}» pendiente —</div>
          )}
        </main>
      </div>
    </div>
  );
}
