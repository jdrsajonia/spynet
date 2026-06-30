// Mapa embebido (OpenStreetMap) que muestra un pin en las coordenadas de la IP.
// Sin API key ni dependencias: solo un <iframe>. El estilo vive en analyse.css.
export default function MapEmbed({ lat, lon, zoom = 0.05 }) {
  if (lat == null || lon == null) {
    return <p className="muted">No coordinates available.</p>;
  }

  // bbox = pequeño recuadro alrededor del punto (controla el "zoom").
  const bbox = [lon - zoom, lat - zoom, lon + zoom, lat + zoom].join("%2C");
  const src = `https://www.openstreetmap.org/export/embed.html?bbox=${bbox}&layer=mapnik&marker=${lat}%2C${lon}`;
  const fullMap = `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=12/${lat}/${lon}`;

  return (
    <div className="geo__map">
      <iframe className="map" title="IP location" src={src} loading="lazy" />
      <a className="card__more" href={fullMap} target="_blank" rel="noreferrer">
        View larger map ↗
      </a>
    </div>
  );
}
