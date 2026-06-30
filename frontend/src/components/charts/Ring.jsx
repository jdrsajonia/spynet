// Anillo de progreso (un solo valor 0–100) en SVG. Para "Avg Confidence".
export default function Ring({ value = 0 }) {
  const R = 58;
  const C = 2 * Math.PI * R;
  const len = (Math.min(Math.max(value, 0), 100) / 100) * C;

  return (
    <svg viewBox="0 0 160 160" className="ring">
      <g transform="translate(80,80) rotate(-90)">
        <circle r={R} className="ring__track" />
        <circle r={R} className="ring__fg" strokeDasharray={`${len} ${C - len}`} />
      </g>
      <text x="80" y="88" textAnchor="middle" className="ring__num">{value}%</text>
    </svg>
  );
}
