import { useState } from "react";

// Barra superior: marca + buscador de URL. Es "tonto": solo emite onSearch(url).
// Quien decide qué hacer con esa URL es el contenedor (App).
export default function Topbar({ onSearch, busy }) {
  const [url, setUrl] = useState("");

  return (
    <header className="topbar">
      <div className="topbar__brand">
        <h1>SPY<b>NET</b></h1>
        <p>Web Intelligence</p>
      </div>
      <div className="topbar__search">
        <input
          placeholder="Enter URL to analyse…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSearch(url)}
        />
        <button type="button" onClick={() => onSearch(url)} disabled={busy} aria-label="Analyse">
          →
        </button>
      </div>
    </header>
  );
}
