// Iconos de línea (SVG) para la navegación. Separados para no ensuciar el JSX.
const base = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round", strokeLinejoin: "round" };

export const Icon = {
  home: (
    <svg className="nav__icon" {...base}><path d="M3 11l9-8 9 8" /><path d="M5 10v10h5v-6h4v6h5V10" /></svg>
  ),
  analyse: (
    <svg className="nav__icon" {...base}><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></svg>
  ),
  historical: (
    <svg className="nav__icon" {...base}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
  ),
  dashboard: (
    <svg className="nav__icon" {...base}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></svg>
  ),
  compare: (
    <svg className="nav__icon" {...base}><path d="M7 8l-4 4 4 4" /><path d="M17 8l4 4-4 4" /><path d="M3 12h18" /></svg>
  ),
  apidocs: (
    <svg className="nav__icon" {...base}><path d="M8 6l-5 6 5 6" /><path d="M16 6l5 6-5 6" /></svg>
  ),
};
