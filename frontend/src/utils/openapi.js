// Lectura del documento OpenAPI 3 que sirve el backend en /api/v1/schema/.
// Aísla las rarezas del formato ($ref, allOf, additionalProperties, nodos sin
// tipo) para que la vista solo tenga que pintar.

const METHODS = ["get", "post", "put", "patch", "delete"];

const refName = (ref) => ref.split("/").pop();

function byRef(root, ref) {
  return ref.replace(/^#\//, "").split("/").reduce((acc, key) => acc?.[key], root);
}

/** Sigue $ref y aplana `allOf: [$ref]` (así emite drf-spectacular los campos nullable). */
export function resolve(node, root) {
  if (!node || typeof node !== "object") return node;
  if (node.$ref) return resolve(byRef(root, node.$ref), root);
  if (Array.isArray(node.allOf) && node.allOf.length === 1) {
    const { allOf, ...rest } = node;
    return { ...resolve(allOf[0], root), ...rest };
  }
  return node;
}

/** Nombre del componente al que apunta el nodo, si apunta a alguno. */
export function componentName(node) {
  if (node?.$ref) return refName(node.$ref);
  if (node?.allOf?.length === 1 && node.allOf[0].$ref) return refName(node.allOf[0].$ref);
  return null;
}

/** Etiqueta legible del tipo: `string`, `Analysis`, `Technology[]`, `map<string, string>`… */
export function typeLabel(node, root) {
  const n = resolve(node, root);
  // Un nodo sin `type` es un JSONField: acepta cualquier JSON.
  if (!n || (!n.type && !n.enum && !n.properties)) return "json";
  if (n.enum) return n.enum.map((v) => `"${v}"`).join(" | ");
  if (n.type === "array") return `${typeLabel(n.items, root)}[]`;
  if (n.additionalProperties) return `map<string, ${typeLabel(n.additionalProperties, root)}>`;
  if (n.type === "object" || n.properties) return componentName(node) || "object";
  return n.format ? `${n.type}<${n.format}>` : n.type;
}

/** Campos de un objeto, con su bandera de obligatorio. `[]` si no es un objeto con propiedades. */
export function fieldsOf(node, root) {
  const n = resolve(node, root);
  if (!n?.properties) return [];
  const required = new Set(n.required || []);
  return Object.entries(n.properties).map(([name, child]) => ({
    name,
    node: child,
    resolved: resolve(child, root),
    required: required.has(name),
  }));
}

/** Campos anidados que merecen despliegue: objeto → sus campos; array de objetos → los del item. */
export function childFields(node, root) {
  const n = resolve(node, root);
  if (!n) return [];
  if (n.additionalProperties) return [];   // un mapa se describe con su typeLabel
  if (n.type === "array") return fieldsOf(n.items, root);
  return fieldsOf(n, root);
}

const jsonOf = (holder) => holder?.content?.["application/json"]?.schema;

export const requestSchema = (op) => jsonOf(op.requestBody);
export const responseSchema = (response) => jsonOf(response);

/** Todas las operaciones del documento, aplanadas. */
export function operations(root) {
  const out = [];
  for (const [path, item] of Object.entries(root.paths || {})) {
    for (const method of METHODS) {
      const op = item[method];
      if (!op) continue;
      out.push({
        key: `${method}:${path}`,
        method: method.toUpperCase(),
        path,
        tag: op.tags?.[0] || "other",
        summary: op.summary || op.operationId,
        description: op.description || "",
        parameters: op.parameters || [],
        requestBody: op.requestBody,
        responses: op.responses || {},
      });
    }
  }
  return out;
}

/** Agrupa por tag, respetando el orden declarado en `tags` del documento. */
export function groupByTag(ops, root) {
  const order = (root.tags || []).map((t) => t.name);
  const rank = (tag) => (order.indexOf(tag) === -1 ? order.length : order.indexOf(tag));
  const groups = new Map();
  for (const op of ops) {
    if (!groups.has(op.tag)) groups.set(op.tag, []);
    groups.get(op.tag).push(op);
  }
  return [...groups.entries()]
    .sort((a, b) => rank(a[0]) - rank(b[0]))
    .map(([tag, items]) => ({
      tag,
      description: (root.tags || []).find((t) => t.name === tag)?.description || "",
      items,
    }));
}

/**
 * `call()` ya lleva el prefijo del backend en su URL base, así que las rutas del
 * documento (`/api/v1/analyses/`) hay que servirlas sin él.
 */
export function stripBasePath(path, apiBase) {
  let prefix = "";
  try {
    prefix = new URL(apiBase).pathname.replace(/\/$/, "");
  } catch {
    prefix = apiBase.replace(/\/$/, "");
  }
  return prefix && path.startsWith(prefix) ? path.slice(prefix.length) : path;
}
