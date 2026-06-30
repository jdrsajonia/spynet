// Donut chart en SVG puro (sin librerías). Recibe segmentos [{label,value,color}].
// La geometría (dasharray/offset) es lógica; el color viene como dato por segmento.
export default function Donut({ segments, total, centerLabel = "Total" }) {
  const sum = segments.reduce((s, x) => s + x.value, 0) || 1;
  const R = 58;
  const C = 2 * Math.PI * R;
  let offset = 0;

  return (
    <svg viewBox="0 0 160 160" className="donut">
      <g transform="translate(80,80) rotate(-90)">
        <circle r={R} className="donut__track" />
        {segments.map((seg) => {
          const len = (seg.value / sum) * C;
          const circle = (
            <circle
              key={seg.label}
              r={R}
              className="donut__seg"
              style={{ stroke: seg.color }}
              strokeDasharray={`${len} ${C - len}`}
              strokeDashoffset={-offset}
            />
          );
          offset += len;
          return circle;
        })}
      </g>
      <text x="80" y="76" textAnchor="middle" className="donut__num">{total}</text>
      <text x="80" y="95" textAnchor="middle" className="donut__lbl">{centerLabel}</text>
    </svg>
  );
}
