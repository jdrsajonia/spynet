// Capa única que habla con el backend. La URL base viene de una variable de
// entorno (.env) — nunca hardcodeada — con un fallback para desarrollo local.
const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

/**
 * Hace la petición y devuelve { status, body } SIEMPRE (también en 4xx/5xx),
 * para que el probador pueda mostrar la respuesta cruda pase lo que pase.
 */
export async function call(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  let body;
  try {
    body = await res.json();
  } catch {
    body = { _note: "respuesta no-JSON" };
  }

  return { status: res.status, body };
}

export const API_BASE = BASE;
