// Gráfica de línea (área) en SVG para "Activity Overview". points = [{label,value}].
export default function LineChart({ points }) {
  const W = 600, H = 190, pad = 12;
  if (!points || points.length === 0) {
    return <div className="muted">Sin actividad todavía.</div>;
  }

  const max = Math.max(...points.map((p) => p.value), 1);
  const stepX = (W - pad * 2) / Math.max(points.length - 1, 1);
  const xy = points.map((p, i) => [
    pad + i * stepX,
    H - pad - (p.value / max) * (H - pad * 2),
  ]);

  const line = xy.map((c) => c.join(",")).join(" ");
  const area = `${pad},${H - pad} ${line} ${W - pad},${H - pad}`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="linechart" preserveAspectRatio="none">
      <polygon className="linechart__area" points={area} />
      <polyline className="linechart__line" points={line} />
      {xy.map((c, i) => (
        <circle key={i} cx={c[0]} cy={c[1]} r="2.5" className="linechart__dot" />
      ))}
    </svg>
  );
}
