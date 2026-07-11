// Vista Home: landing de presentación del proyecto. Es puramente presentacional
// (no pide datos). Reutiliza la clase base .card y los tokens del sistema.
export default function HomeView() {
  return (
    <div className="home">
      {/* HERO */}
      
      {/* <header className="home-hero">
        <h1 className="home-hero__title">SPY<b>NET</b></h1>
        <p className="home-hero__subtitle">
          Web Intelligence · Technology Mapping · OSINT Analysis
        </p>
      </header> */}

      {/* BANNER */}
      <section className="home-banner">
        <picture>
          {/* WebP ligero (~34 KB) para navegadores modernos; PNG como fallback */}
          <source srcSet="/spynet_penguins.webp" type="image/webp" />
          <img
            src="/spynet_penguins.png"
            alt="Spynet banner"
            width={1672}
            height={941}
            fetchPriority="high"
            onError={(e) => { e.currentTarget.parentElement.parentElement.style.display = "none"; }}
          />
        </picture>
      </section>

      {/* ABOUT */}
      <section className="home-section">
        <h2 className="home-h2">What is Spynet?</h2>
        <p className="home-prose">
          <strong>Spynet</strong> is a web intelligence platform designed to analyze,
          map and understand the technological composition of modern websites.
          Through OSINT techniques and infrastructure analysis, the system provides
          structured insights about technologies, integrations and services behind a domain.
        </p>
      </section>

      {/* FEATURES */}
      <section className="home-section">
        <h2 className="home-h2">Core Features</h2>
        <div className="home-cards">
          <article className="card home-card">
            <h3 className="home-card__title">Technology Mapping</h3>
            <p>Detect frontend frameworks, backend technologies, servers and third-party integrations.</p>
          </article>

          <article className="card home-card">
            <h3 className="home-card__title">Infrastructure Analysis</h3>
            <p>Gather DNS, WHOIS and hosting-related information to better understand a website's infrastructure.</p>
          </article>

          <article className="card home-card">
            <span className="home-badge">Experimental</span>
            <h3 className="home-card__title">Historical Intelligence</h3>
            <p>Explore historical snapshots and technological evolution through archived web data.</p>
          </article>
        </div>
      </section>

      {/* REST API */}
      <section className="home-section">
        <h2 className="home-h2">REST API</h2>
        <p className="home-prose">
          Spynet also acts as a REST API capable of exposing structured analysis
          results for external systems, scripts and integrations.
        </p>
      </section>

      {/* MASCOT */}
      <section className="home-mascot">
        <img
          src="/tux_spynet_profesional.webp"
          alt="Spynet Tux"
          onError={(e) => { e.currentTarget.style.display = "none"; }}
        />
        <p>Watching every system.<br />Auditing every weakness.</p>
      </section>

      {/* FOOTER */}
      <footer className="home-footer">
        <p>© 2026 Spynet · Developed by Spynella Team | Los Extraditables</p>
      </footer>
    </div>
  );
}
