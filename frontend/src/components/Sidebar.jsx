// Componente presentacional: solo pinta la navegación. No sabe de datos ni de
// estilos concretos (todo viene de layout.css). Recibe items + estado por props.
export default function Sidebar({ items, active, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="sidebar__logo">
        {/* Coloca la imagen en frontend/public/logo.png */}
        <img
          className="sidebar__logo-img"
          src="/tux_spynet_profesional.png"
          alt=""
          onError={(e) => { e.currentTarget.style.display = "none"; }}
        />
        SPY<b>NET</b>
      </div>
      <nav className="nav">
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            className={"nav__item" + (item.key === active ? " is-active" : "")}
            disabled={item.disabled}
            onClick={() => onSelect(item.key)}
          >
            {item.icon}
            {item.label}
          </button>
        ))}
      </nav>
    </aside>
  );
}
