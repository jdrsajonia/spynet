import { useMemo, useState } from "react";

import { API_BASE, call } from "../api";
import {
  childFields,
  fieldsOf,
  groupByTag,
  operations,
  requestSchema,
  resolve,
  responseSchema,
  stripBasePath,
  typeLabel,
} from "../utils/openapi";

// Vista "API Docs": documentación navegable + probador, ambos generados desde el
// documento OpenAPI que sirve el backend. Nada está escrito a mano aquí, así que
// no puede quedar desincronizada: si cambia una vista de Django, cambia esto.
//
// El esquema llega por props (lo pide el contenedor). El estado de navegación y
// el del probador son locales: son interacción de la vista, no datos de la app.

export default function ApiDocsView({ schema, loading, error }) {
  const [selected, setSelected] = useState(null);
  const [query, setQuery] = useState("");

  const groups = useMemo(() => {
    if (!schema) return [];
    return groupByTag(operations(schema), schema);
  }, [schema]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return groups;
    return groups
      .map((g) => ({
        ...g,
        items: g.items.filter(
          (op) =>
            op.path.toLowerCase().includes(q) ||
            op.method.toLowerCase().includes(q) ||
            op.summary.toLowerCase().includes(q)
        ),
      }))
      .filter((g) => g.items.length > 0);
  }, [groups, query]);

  if (loading) return <div className="placeholder">Loading the API scheme…</div>;
  if (error) return <div className="error">{error}</div>;
  if (!schema) return null;

  const op = selected && operations(schema).find((o) => o.key === selected);

  return (
    <section>
      <header className="view-head">
        <h2 className="view-head__title">{schema.info.title}</h2>
        <p className="view-head__meta">
          v{schema.info.version} · <code>{API_BASE}</code> · Generated from backend
        </p>
      </header>

      <div className="docs">
        <aside className="docs__nav card">
          <input
            className="docs__search"
            placeholder="Filter endpoints…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="button"
            className={"docs__overview" + (selected ? "" : " is-active")}
            onClick={() => setSelected(null)}
          >
            Overview
          </button>

          {filtered.map((group) => (
            <div className="docs__group" key={group.tag}>
              <div className="docs__group-title">{group.tag}</div>
              {group.items.map((item) => (
                <button
                  type="button"
                  key={item.key}
                  className={"docs__op" + (item.key === selected ? " is-active" : "")}
                  onClick={() => setSelected(item.key)}
                >
                  <Method value={item.method} />
                  <span className="docs__op-path">{stripBasePath(item.path, API_BASE)}</span>
                </button>
              ))}
            </div>
          ))}
          {filtered.length === 0 && <p className="muted">No endpoint matches.</p>}
        </aside>

        <div className="docs__main">
          {op ? <Operation op={op} root={schema} /> : <Overview info={schema.info} groups={groups} />}
        </div>
      </div>
    </section>
  );
}

// ── overview ──────────────────────────────────────────────────────────────────

function Overview({ info, groups }) {
  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> Overview</h3>
      <RichText className="docs__prose" text={info.description} />
      <div className="docs__counts">
        {groups.map((g) => (
          <div className="docs__count" key={g.tag}>
            <div className="stat__num">{g.items.length}</div>
            <div className="stat__label">{g.tag}</div>
          </div>
        ))}
      </div>
    </article>
  );
}

// ── una operación ─────────────────────────────────────────────────────────────

function Operation({ op, root }) {
  const pathParams = op.parameters.filter((p) => p.in === "path");
  const queryParams = op.parameters.filter((p) => p.in === "query");
  const body = requestSchema(op);
  const bodyFields = body ? fieldsOf(body, root) : [];

  return (
    <>
      <article className="card">
        <div className="docs__head">
          <Method value={op.method} />
          <code className="docs__path">{op.path}</code>
        </div>
        <h3 className="docs__summary">{op.summary}</h3>
        <RichText className="docs__prose" text={op.description} />
      </article>

      {(pathParams.length > 0 || queryParams.length > 0) && (
        <article className="card">
          <h3 className="card__title"><span className="dot" /> Parameters</h3>
          <table className="docs__params">
            <tbody>
              {[...pathParams, ...queryParams].map((p) => (
                <tr key={`${p.in}:${p.name}`}>
                  <td className="docs__params-name">
                    <code>{p.name}</code>
                    {p.required && <span className="docs__req">*</span>}
                  </td>
                  <td><span className="docs__type">{typeLabel(p.schema, root)}</span></td>
                  <td><span className="docs__in">{p.in}</span></td>
                  <td className="muted">{p.description || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      )}

      {bodyFields.length > 0 && (
        <article className="card">
          <h3 className="card__title"><span className="dot" /> Request body</h3>
          <p className="docs__ctype">application/json</p>
          <SchemaTree fields={bodyFields} root={root} depth={0} />
        </article>
      )}

      <CurlExample op={op} root={root} pathParams={pathParams} queryParams={queryParams} bodyFields={bodyFields} />

      <TryIt key={op.key} op={op} root={root} pathParams={pathParams} queryParams={queryParams} bodyFields={bodyFields} />

      <article className="card">
        <h3 className="card__title"><span className="dot" /> Responses</h3>
        {Object.entries(op.responses)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([code, response]) => (
            <Response key={code} code={code} response={response} root={root} />
          ))}
      </article>
    </>
  );
}

function Response({ code, response, root }) {
  const body = responseSchema(response);
  const fields = body ? fieldsOf(body, root) : [];
  return (
    <div className="docs__response">
      <div className="docs__response-head">
        <Status code={code} />
        <span className="muted">{response.description || ""}</span>
      </div>
      {fields.length > 0 && <SchemaTree fields={fields} root={root} depth={0} />}
    </div>
  );
}

// ── árbol de esquema ──────────────────────────────────────────────────────────

function SchemaTree({ fields, root, depth }) {
  return (
    <div className="docs__tree">
      {fields.map((f) => (
        <SchemaField key={f.name} field={f} root={root} depth={depth} />
      ))}
    </div>
  );
}

function SchemaField({ field, root, depth }) {
  const kids = childFields(field.node, root);
  // Se despliega solo lo cercano a la raíz: `data` y `meta` abiertos, el resto no.
  const [open, setOpen] = useState(depth < 1);
  const resolved = field.resolved || resolve(field.node, root);
  const expandable = kids.length > 0;

  return (
    <div className="docs__field">
      <div className="docs__field-row">
        <button
          type="button"
          className={"docs__toggle" + (expandable ? "" : " is-leaf")}
          onClick={() => expandable && setOpen(!open)}
          disabled={!expandable}
          aria-label={expandable ? (open ? "Contraer" : "Expandir") : undefined}
        >
          {expandable ? (open ? "−" : "+") : "·"}
        </button>
        <code className="docs__field-name">{field.name}</code>
        {field.required && <span className="docs__req">*</span>}
        <span className="docs__type">{typeLabel(field.node, root)}</span>
        {resolved?.nullable && <span className="docs__nullable">nullable</span>}
      </div>
      {resolved?.description && (
        <RichText className="docs__field-desc" text={resolved.description} />
      )}
      {expandable && open && (
        <div className="docs__nested">
          <SchemaTree fields={kids} root={root} depth={depth + 1} />
        </div>
      )}
    </div>
  );
}

// ── ejemplo cURL ──────────────────────────────────────────────────────────────

// Un valor de muestra para el body, según el tipo del campo. La idea no es dar un
// valor real (imposible saberlo), sino enseñar la ESTRUCTURA: qué clave lleva y
// de qué tipo es. Los placeholders van entre <…> para que se vean como "rellename".
function sampleValue(label) {
  if (label === "integer" || label === "number") return 0;
  if (label === "boolean") return true;
  if (label === "json") return {};
  if (label.endsWith("[]")) return [];
  if (label.startsWith("map<")) return {};
  return `<${label}>`;
}

// Resuelve API_BASE a una URL absoluta para que el curl muestre siempre el host
// completo. Si API_BASE ya es absoluta (trae protocolo+host), la respeta. Si es
// relativa (p. ej. "/api/v1" detrás del proxy nginx), la ancla al origen desde
// donde se sirve la página: así sale la IP pública en producción o localhost en
// dev, sin nada hardcodeado.
function absoluteBase(apiBase) {
  try {
    return new URL(apiBase).href.replace(/\/$/, "");
  } catch {
    const origin =
      typeof window !== "undefined"
        ? window.location.origin
        : "http://localhost:8000";
    return `${origin}${apiBase}`.replace(/\/$/, "");
  }
}

// Construye el comando curl desde el propio esquema, así nunca se desincroniza del
// backend. Path params → <name> en la URL; query params → ?k=<tipo>; body → -d con
// un JSON de muestra. GET no lleva -X ni body.
function curlSnippet({ op, root, pathParams, queryParams, bodyFields }) {
  let path = stripBasePath(op.path, API_BASE);
  for (const p of pathParams) {
    path = path.replace(`{${p.name}}`, `<${p.name}>`);
  }
  const qs = queryParams
    .map((p) => `${p.name}=<${typeLabel(p.schema, root)}>`)
    .join("&");
  if (qs) path += `?${qs}`;

  const url = `${absoluteBase(API_BASE)}${path}`;
  const method = op.method.toUpperCase();
  const methodFlag = method === "GET" ? "" : `-X ${method} `;

  if (bodyFields.length > 0) {
    const sample = {};
    for (const f of bodyFields) sample[f.name] = sampleValue(typeLabel(f.node, root));
    const json = JSON.stringify(sample, null, 2);
    return `curl ${methodFlag}"${url}" \\\n  -H "Content-Type: application/json" \\\n  -d '${json}'`;
  }
  return `curl ${methodFlag}"${url}"`;
}

function CurlExample({ op, root, pathParams, queryParams, bodyFields }) {
  const snippet = useMemo(
    () => curlSnippet({ op, root, pathParams, queryParams, bodyFields }),
    [op, root, pathParams, queryParams, bodyFields]
  );
  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> cURL example</h3>
      <p className="muted">
        Usage example with cURL
        
      </p>
      <pre className="docs__json docs__curl">{snippet}</pre>
    </article>
  );
}

// ── probador ──────────────────────────────────────────────────────────────────

// Un campo se edita como JSON crudo cuando no es un escalar: objetos libres
// (`json`), arrays y mapas. El resto son inputs normales.
const isRawJson = (label) => label === "json" || label.endsWith("[]") || label.startsWith("map<");

function TryIt({ op, root, pathParams, queryParams, bodyFields }) {
  const [values, setValues] = useState({});
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  const set = (name, value) => setValues((v) => ({ ...v, [name]: value }));
  const inputs = [
    ...pathParams.map((p) => ({ name: p.name, label: typeLabel(p.schema, root), where: "path", required: p.required })),
    ...queryParams.map((p) => ({ name: p.name, label: typeLabel(p.schema, root), where: "query", required: p.required })),
    ...bodyFields.map((f) => ({ name: f.name, label: typeLabel(f.node, root), where: "body", required: f.required })),
  ];

  async function run() {
    setBusy(true);
    setResult(null);
    try {
      let path = stripBasePath(op.path, API_BASE);
      for (const p of pathParams) {
        path = path.replace(`{${p.name}}`, encodeURIComponent(values[p.name] ?? ""));
      }
      const qs = queryParams
        .filter((p) => values[p.name] !== undefined && values[p.name] !== "")
        .map((p) => `${p.name}=${encodeURIComponent(values[p.name])}`)
        .join("&");
      if (qs) path += `?${qs}`;

      let payload;
      if (bodyFields.length > 0) {
        payload = {};
        for (const f of bodyFields) {
          const raw = values[f.name];
          if (raw === undefined || raw === "") continue;
          payload[f.name] = isRawJson(typeLabel(f.node, root)) ? JSON.parse(raw) : raw;
        }
      }

      const { status, body } = await call(path, {
        method: op.method,
        body: payload ? JSON.stringify(payload) : undefined,
      });
      setResult({ status, body });
    } catch (err) {
      const hint =
        err instanceof SyntaxError
          ? "A JSON field is invalid."
          : "Is the backend running on :8000?";
      setResult({ status: null, body: { _error: `${err.message} — ${hint}` } });
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="card">
      <h3 className="card__title"><span className="dot" /> Try it</h3>
      {inputs.length === 0 && <p className="muted">This endpoint does not require parameters.</p>}

      {inputs.map((f) => (
        <label className="docs__input-row" key={`${f.where}:${f.name}`}>
          <span className="docs__input-label">
            <code>{f.name}</code>
            {f.required && <span className="docs__req">*</span>}
            <span className="docs__in">{f.where}</span>
          </span>
          {isRawJson(f.label) ? (
            <textarea
              className="docs__textarea"
              rows={3}
              placeholder={f.label === "json" ? "{ … }" : "[ … ]"}
              value={values[f.name] || ""}
              onChange={(e) => set(f.name, e.target.value)}
            />
          ) : (
            <input
              className="docs__input"
              type={f.label === "integer" ? "number" : "text"}
              placeholder={f.label}
              value={values[f.name] || ""}
              onChange={(e) => set(f.name, e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && run()}
            />
          )}
        </label>
      ))}

      <button className="docs__run" onClick={run} disabled={busy}>
        {busy ? "…" : `Ejecutar ${op.method}`}
      </button>

      {result && (
        <div className="docs__result">
          <div className="docs__result-head">
            {result.status ? <Status code={String(result.status)} /> : <span className="docs__status is-5xx">error</span>}
          </div>
          <pre className="docs__json">{JSON.stringify(result.body, null, 2)}</pre>
        </div>
      )}
    </article>
  );
}

// ── piezas pequeñas ───────────────────────────────────────────────────────────

const Method = ({ value }) => (
  <span className={`docs__method is-${value.toLowerCase()}`}>{value}</span>
);

const Status = ({ code }) => (
  <span className={`docs__status is-${code[0]}xx`}>{code}</span>
);

/** Markdown mínimo: el que de verdad usan las descripciones del esquema. */
function RichText({ text, className }) {
  if (!text) return null;
  const blocks = text.split(/```(?:\w+)?\n([\s\S]*?)```/);
  return (
    <div className={className}>
      {blocks.map((block, i) =>
        // Los índices impares son el contenido capturado de un bloque cercado.
        i % 2 === 1 ? (
          <pre className="docs__json" key={i}>{block.trim()}</pre>
        ) : (
          block
            .split("\n\n")
            .filter((p) => p.trim())
            .map((para, j) => <p key={`${i}-${j}`}>{inline(para)}</p>)
        )
      )}
    </div>
  );
}

function inline(text) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, i) => {
    if (part.startsWith("`") && part.endsWith("`")) return <code key={i}>{part.slice(1, -1)}</code>;
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    return part;
  });
}
