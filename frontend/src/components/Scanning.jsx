// Pantalla centrada que se muestra mientras corre un análisis.
// Coloca la imagen en frontend/public/scanning.png
export default function Scanning({ text = "We, the exegetes of the web, are scanning for you…" }) {
  return (
    <div className="scanning">
      <img
        className="scanning__img"
        src="/tux_spynet_profesional.png"
        alt=""
        onError={(e) => { e.currentTarget.style.display = "none"; }}
      />
      <p className="scanning__text">{text}</p>
    </div>
  );
}
