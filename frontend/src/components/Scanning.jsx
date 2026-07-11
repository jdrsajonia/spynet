// Pantalla centrada que se muestra mientras corre un análisis.
// Coloca la imagen en frontend/public/scanning.png
export default function Scanning({ text = "Exegetes of the web, decoding this site's every layer…" }) {
  return (
    <div className="scanning">
      <img
        className="scanning__img"
        src="/tux_spynet_profesional.webp"
        alt=""
        onError={(e) => { e.currentTarget.style.display = "none"; }}
      />
      <p className="scanning__text">{text}</p>
    </div>
  );
}
