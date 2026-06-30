import { useState, useEffect } from "react";

import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import { Icon } from "./components/icons";
import AnalyseView from "./views/AnalyseView";
import CompareView from "./views/CompareView";
import DashboardView from "./views/DashboardView";
import ApiTesterView from "./views/ApiTesterView";
import { call } from "./api";

import "./styles/tokens.css";
import "./styles/layout.css";
import "./styles/analyse.css";
import "./styles/compare.css";
import "./styles/dashboard.css";

// El contenedor: aquí vive el ESTADO y la LÓGICA (qué se pide al backend). Las
// vistas y el shell son presentacionales y solo reciben props. Esto mantiene la
// lógica separada de la presentación.
const NAV = [
  { key: "analyse",    label: "Analyse",    icon: Icon.analyse },
  { key: "historical", label: "Historical", icon: Icon.historical, disabled: true },
  { key: "dashboard",  label: "Dashboard",  icon: Icon.dashboard },
  { key: "compare",    label: "Compare",    icon: Icon.compare },
  { key: "apidocs",    label: "API Docs",   icon: Icon.apidocs,    disabled: true },
  { key: "tester",     label: "API Tester", icon: Icon.tester },
];

export default function App() {
  const [view, setView] = useState("analyse");
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

  // El dashboard es de solo lectura: se carga al entrar a la pestaña.
  useEffect(() => {
    if (view !== "dashboard" || dashData || dashLoading) return;
    (async () => {
      setDashLoading(true);
      setDashError(null);
      try {
        const [statsRes, listRes] = await Promise.all([
          call("/stats/"),
          call("/analyses/?page_size=6"),
        ]);
        if (statsRes.body.success && listRes.body.success) {
          setDashData({ stats: statsRes.body.data, recent: listRes.body.data });
        } else {
          setDashError("Error cargando el dashboard.");
        }
      } catch {
        setDashError("No se pudo conectar con el backend (¿corriendo en :8000?).");
      } finally {
        setDashLoading(false);
      }
    })();
  }, [view, dashData, dashLoading]);

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
      setError("No se pudo conectar con el backend (¿corriendo en :8000?).");
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
      setCmpError("No se pudo conectar con el backend (¿corriendo en :8000?).");
    } finally {
      setCmpLoading(false);
    }
  }

  return (
    <div className="app">
      <Sidebar items={NAV} active={view} onSelect={setView} />
      <div>
        <Topbar onSearch={runAnalyze} busy={loading} />
        <main className="content">
          {view === "analyse" && (
            <AnalyseView
              data={data}
              loading={loading}
              error={error}
              wayback={wayback}
              onRetryWayback={() => data?.id && loadWayback(data.id)}
            />
          )}
          {view === "compare" && (
            <CompareView data={cmpData} loading={cmpLoading} error={cmpError} onCompare={runCompare} />
          )}
          {view === "dashboard" && (
            <DashboardView data={dashData} loading={dashLoading} error={dashError} />
          )}
          {view === "tester" && <ApiTesterView />}
          {!["analyse", "compare", "dashboard", "tester"].includes(view) && (
            <div className="placeholder">— vista «{view}» pendiente —</div>
          )}
        </main>
      </div>
    </div>
  );
}
