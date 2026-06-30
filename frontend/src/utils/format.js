// Helpers de presentación (formateo de datos). No tocan estilos ni estructura.

export function confClass(confidence) {
  if (confidence >= 80) return "conf--high";
  if (confidence >= 50) return "conf--mid";
  return "conf--low";
}

export function yearOf(timestamp = "") {
  return timestamp.slice(0, 4) || "—";
}

export function prettyDate(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString();
}

export function avgConfidence(techs = []) {
  if (!techs.length) return 0;
  return Math.round(techs.reduce((s, t) => s + (t.confidence || 0), 0) / techs.length);
}

export function seconds(ms) {
  return ms == null ? "—" : (ms / 1000).toFixed(2) + "s";
}

// Variante "if_" de Wayback: sirve la captura SIN la barra de herramientas,
// ideal para embeberla como miniatura limpia.
export function snapshotThumbUrl(url, timestamp) {
  return url.replace(`/${timestamp}/`, `/${timestamp}if_/`);
}
