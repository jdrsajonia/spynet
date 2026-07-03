// Colores de categoría de tecnología, compartidos por el donut del Dashboard y
// las bolitas de la lista de Technologies en Analyse. Un único origen para que
// ambos siempre coincidan.
export const CATEGORIES = [
  { key: "frontend",  label: "Frontend",  color: "#3b82f6" },
  { key: "backend",   label: "Backend",   color: "#ef4444" },
  { key: "cdn",       label: "CDN",       color: "#a855f7" },
  { key: "server",    label: "Server",    color: "#22c55e" },
  { key: "analytics", label: "Analytics", color: "#f59e0b" },
];

export const CATEGORY_COLORS = Object.fromEntries(
  CATEGORIES.map((c) => [c.key, c.color])
);

// Color de una categoría; gris neutro si es desconocida.
export function categoryColor(category) {
  return CATEGORY_COLORS[category] || "#64748b";
}
