"""
Asistente de IA para el chat del panel Analyse.

Sin dependencias de modelos Django — trabaja con dicts puros que llegan del
frontend. Usa ``urllib.request`` (stdlib) para llamar a Gemini; si la clave no
está configurada o falla, cae a un resumen determinista del análisis.
"""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# Límites para no exceder tokens de Gemini ni enviar payloads enormes.
_MAX_CONTEXT_CHARS = 12000
_MAX_HISTORY_TURNS = 6  # últimos 6 mensajes (3 pares user/assistant)

# Tipos DNS que se listan primero; el resto (SOA, CAA, …) va detrás, sin perderse.
_DNS_TYPES = ("A", "AAAA", "CNAME", "NS", "MX")


# ── contexto textual ─────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int = 300) -> str:
    if not text or len(text) <= max_len:
        return text or ""
    return text[:max_len] + "…"


def _empty(value) -> bool:
    """Vacío = ausente. Ojo: 0 y False NO son vacíos (un cert con 0 días vive)."""
    return value is None or value == "" or (isinstance(value, (list, tuple, dict)) and not value)


def _render(value) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _fields(data: dict, fields: list[tuple[str, str]]) -> list[str]:
    """[(clave, etiqueta), …] → ["  Etiqueta: valor", …] para las claves con valor."""
    return [
        f"  {label}: {_render(data[key])}"
        for key, label in fields
        if not _empty(data.get(key))
    ]


def build_context(analysis: dict) -> str:
    """Convierte el dict del análisis en un bloque de texto compacto para el LLM."""
    a = analysis
    parts = [
        f"Analyzed URL: {a.get('url', '?')}",
        f"Domain: {a.get('domain', '?')}",
        f"Analysis status: {a.get('status', '?')}",
    ]
    parts += _fields(a, [
        ("analyzed_at", "Analyzed at"), ("duration_ms", "Duration (ms)"),
        ("triggered_by", "Triggered by"),
    ])
    tags = a.get("tags") or {}
    if tags:
        parts.append("  Tags: " + ", ".join(f"{k}={v}" for k, v in tags.items()))

    # Fallos parciales: la diferencia entre "el dato no existe" y "el servicio falló".
    errors = a.get("errors") or []
    if errors:
        parts.append(
            "Services that FAILED during this analysis (their data is missing because of "
            "the failure, not because it doesn't exist — say so if asked):\n"
            + "\n".join(
                f"  {e.get('service', '?')}: {e.get('code') or 'error'}"
                + (f" — {_truncate(e.get('message', ''), 120)}" if e.get("message") else "")
                for e in errors
            )
        )

    # Technologies
    techs = a.get("technologies") or []
    if techs:
        items = []
        for t in techs:
            entry = t.get("name", "?")
            if t.get("version"):
                entry += f" v{t['version']}"
            entry += f" ({t.get('category', '?')}, {t.get('confidence', '?')}%)"
            evidence = _truncate(t.get("evidence", ""), 200)
            if evidence:
                entry += f" [{evidence}]"
            items.append(f"  - {entry}")
        parts.append(f"Detected technologies ({len(techs)}):\n" + "\n".join(items))

    # DNS — tipos conocidos primero, luego cualquier otro tipo que traiga el resolver.
    dns = a.get("dns") or {}
    extra_types = [rt for rt in dns if rt not in _DNS_TYPES and rt != "TXT"]
    dns_lines = [
        f"  {rt}: {', '.join(str(v) for v in dns[rt][:10])}"
        for rt in (*_DNS_TYPES, *sorted(extra_types)) if dns.get(rt)
    ]
    txt = dns.get("TXT") or []
    if txt:
        dns_lines.append(f"  TXT ({len(txt)} record(s)):")
        dns_lines += [f"    - {_truncate(str(v), 200)}" for v in txt[:10]]
        if len(txt) > 10:
            dns_lines.append(f"    … and {len(txt) - 10} more TXT record(s)")
    if dns_lines:
        parts.append("DNS records:\n" + "\n".join(dns_lines))

    # WHOIS y Geo (data-driven)
    whois_lines = _fields(a.get("whois") or {}, [
        ("registrar", "Registrar"), ("org", "Organization"), ("registrant", "Registrant"),
        ("country", "Country"), ("creation_date", "Created"), ("expiration_date", "Expires"),
        ("updated_date", "Updated"), ("domain_age_years", "Age (years)"),
        ("status", "EPP status codes"), ("dnssec", "DNSSEC (registry)"),
        ("emails", "Contact emails"),
    ])
    if whois_lines:
        parts.append("WHOIS:\n" + "\n".join(whois_lines))

    geo_lines = _fields(a.get("geo") or {}, [
        ("country", "Country"), ("city", "City"), ("isp", "ISP"),
        ("org", "Organization"), ("ip", "IP"), ("reverse_dns", "Reverse DNS"),
        ("lat", "Latitude"), ("lon", "Longitude"),
    ])
    if geo_lines:
        parts.append("Geolocation:\n" + "\n".join(geo_lines))

    # TLS
    tls = a.get("tls") or {}
    if tls:
        tls_lines = []
        if tls.get("valid") is True:
            tls_lines.append("  Status: valid")
        elif tls.get("valid") is False:
            tls_lines.append(f"  Status: INVALID ({tls.get('error', 'unknown error')})")
        tls_lines += _fields(tls, [
            ("issuer", "Issuer"), ("subject_cn", "Common Name"),
            ("valid_from", "Valid from"), ("valid_to", "Valid until"),
            ("tls_version", "TLS version"), ("days_to_expiry", "Days to expiry"),
        ])
        san = tls.get("san") or []
        if san:
            shown = ", ".join(san[:15])
            more = f" (+{len(san) - 15} more)" if len(san) > 15 else ""
            tls_lines.append(f"  Domains covered (SAN, {len(san)}): {shown}{more}")
        parts.append("SSL/TLS certificate:\n" + "\n".join(tls_lines))

    # Email security
    email = a.get("email_security") or {}
    if email:
        parts.append("Email security:\n" + "\n".join([
            f"  SPF: {_truncate(email['spf'], 200) if email.get('spf') else 'not configured'}",
            f"  DMARC: {_truncate(email['dmarc'], 200) if email.get('dmarc') else 'not configured'}",
            f"  DNSSEC: {'enabled' if email.get('dnssec') else 'not enabled'}",
        ]))

    # Security audit
    security = a.get("security") or {}
    if security:
        findings = security.get("findings") or []
        head = f"Security audit: grade {security.get('grade', '?')}"
        if not _empty(security.get("score")):
            head += f" (score {security['score']}/100)"
        sec_lines = [f"{head}, {len(findings)} finding(s)"]
        for f in findings[:20]:
            line = f"  [{f.get('severity', '?').upper()}] {f.get('title', '?')}"
            if f.get("category"):
                line += f" ({f['category']}"
                line += f", {f['tech']})" if f.get("tech") else ")"
            elif f.get("tech"):
                line += f" ({f['tech']})"
            if f.get("detail"):
                line += f": {_truncate(f['detail'], 200)}"
            sec_lines.append(line)
        if len(findings) > 20:
            sec_lines.append(f"  … and {len(findings) - 20} more finding(s)")
        parts.append("\n".join(sec_lines))

    # Wayback Machine (historial de capturas y su stack en cada momento)
    wayback = a.get("wayback") or {}
    snapshots = wayback.get("snapshots") or []
    if wayback:
        wb_lines = _fields(wayback, [
            ("snapshot_count", "Snapshots stored"), ("archive_pages", "Archive pages (CDX)"),
            ("first_snapshot_at", "First capture"), ("last_snapshot_at", "Last capture"),
        ])
        for s in snapshots[:12]:
            names = [t.get("name", "?") for t in (s.get("technologies") or [])]
            stack = ", ".join(names[:8]) if names else "no technologies detected"
            if len(names) > 8:
                stack += f" (+{len(names) - 8} more)"
            wb_lines.append(f"  {s.get('timestamp', '?')}: {stack}")
        if len(snapshots) > 12:
            wb_lines.append(f"  … and {len(snapshots) - 12} more snapshot(s)")
        if wb_lines:
            parts.append("Wayback Machine history:\n" + "\n".join(wb_lines))

    # Lo que NO está disponible (para que el LLM no se lo invente)
    missing = [name for name, val in [
        ("technologies", techs), ("DNS", dns), ("WHOIS", a.get("whois")),
        ("geolocation", a.get("geo")), ("SSL/TLS", tls), ("email security", email),
        ("security audit", security), ("Wayback history", wayback),
    ] if not val]
    if missing:
        parts.append(f"Data NOT available in this analysis: {', '.join(missing)}")

    return _fit(parts)


def _fit(parts: list[str]) -> str:
    """
    Ajusta el contexto al límite recortando las secciones MÁS LARGAS (típicamente
    tecnologías o TXT), no el final: la auditoría de seguridad y el Wayback van
    al final y son lo último que queremos perder.
    """
    while len("\n".join(parts)) > _MAX_CONTEXT_CHARS:
        idx = max(range(len(parts)), key=lambda i: len(parts[i]))
        longest = parts[idx]
        if len(longest) <= 300:
            break  # ya no queda nada gordo que recortar: corte duro abajo
        excess = len("\n".join(parts)) - _MAX_CONTEXT_CHARS
        keep = max(300, len(longest) - excess - 40)
        parts[idx] = longest[:keep] + "\n  […section truncated due to length]"

    context = "\n".join(parts)
    if len(context) > _MAX_CONTEXT_CHARS:
        context = context[:_MAX_CONTEXT_CHARS] + "\n[context truncated due to length]"
    return context


# ── Gemini (REST, stdlib) ─────────────────────────────────────────────────────

_GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)

_SYSTEM_PROMPT = """\
You are the expert assistant of SpyNet, a web intelligence platform.
Your role is to help the user understand the technical analysis of a website and turn it into clear actions.
You speak like a senior consultant in web technology, architecture, cybersecurity, technical SEO, analytics, performance and user experience.

STYLE:
- Natural and conversational, like an expert colleague.
- Clear, direct, professional but easy to understand.
- Specific to the analyzed site — not generic.
- Action-oriented.
- Not robotic.
- Don't repeat the whole analysis unless asked.
- Don't invent data that isn't in the context.
- No empty generic phrases or filler.
- No unnecessary alarmism.
- Reply in the same language the user uses (default to English).
- Explain technical concepts in simple language.
- Prioritize what matters most first.

FORMAT AND CONTENT RULES:
- Reply in clean Markdown.
- Use short headings, clear bullets and brief paragraphs.
- Don't use tables unless the user explicitly asks for them.
- Use inline code with backticks ONLY for specific technical names like headers, directives, HTTP headers or exact values (e.g. `Strict-Transport-Security`, `DENY`, `SAMEORIGIN`, `includeSubDomains`).
- Don't wrap common words or whole phrases in backticks.
- Avoid deeply nested lists.
- Don't reply as JSON or say "according to the provided context".
- If something isn't in the analysis, say so clearly.
- When the user asks for improvements or recommendations, use simple clear sections:
  1. Quick diagnosis (what is observed).
  2. Priority actions (what to do first).
  3. Expected impact (why it matters).
  4. Recommended next step.
- When asked about risks, separate priority, impact and recommendation.
- When asked for a summary, give a short executive summary.
- Mention positive points when there are any (valid SSL, analytics present, etc.).
- Don't use more than 500 words unless the user asks for detail."""


def ask_gemini(question: str, context: str, history: list[dict]) -> str:
    """Llama a Gemini REST API.  Lanza excepción si falla."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("GEMINI_API_KEY no configurada")
    api_key = api_key.strip()

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    model = model.strip() if model and model.strip() else "gemini-2.5-flash"

    # Contexto como primer intercambio + historial reciente + pregunta actual.
    contents: list[dict] = [
        {"role": "user", "parts": [{"text": f"[CONTEXTO DEL ANÁLISIS WEB]\n{context}"}]},
        {"role": "model", "parts": [{"text": "Understood. I have the full analysis of the site. How can I help?"}]},
    ]
    for msg in (history or [])[-_MAX_HISTORY_TURNS:]:
        text = msg.get("content", "")
        if text:
            role = "model" if msg.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": question}]})

    payload = json.dumps({
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.75, "maxOutputTokens": 2048},
    }).encode()

    url = _GEMINI_BASE_URL.format(model=model, key=api_key)
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            logger.error("Gemini: error de autenticación (HTTP %d). Verifica GEMINI_API_KEY.", e.code)
        elif e.code == 429:
            logger.warning("Gemini: rate limit alcanzado (HTTP 429).")
        else:
            logger.warning("Gemini: HTTP %d.", e.code)
        raise RuntimeError(f"Gemini HTTP {e.code}")
    except urllib.error.URLError as e:
        logger.warning("Gemini: error de red — %s", e.reason)
        raise RuntimeError(f"Gemini network error: {e.reason}")
    except TimeoutError:
        logger.warning("Gemini: timeout tras 30s.")
        raise RuntimeError("Gemini timeout")

    candidates = body.get("candidates") or []
    parts = candidates[0].get("content", {}).get("parts") if candidates else None
    answer = parts[0].get("text", "") if parts else ""
    if not answer.strip():
        logger.warning("Gemini: respuesta vacía — %s", json.dumps(body)[:200])
        raise RuntimeError("Gemini: respuesta vacía")
    return answer


# ── fallback determinista (sin IA externa) ────────────────────────────────────

def ask_local(question: str, context: str, analysis: dict) -> str:
    """
    Fallback when Gemini is unavailable: an honest message + a deterministic
    summary of the analysis. It does not try to be conversational (that's what
    Gemini is for); it just presents the data in a readable way.
    """
    return (
        "The AI assistant needs a configured Gemini API key to answer "
        "conversationally. In the meantime, here's a summary of the analysis:\n\n"
        + _executive_summary(analysis)
    )


def _executive_summary(analysis: dict) -> str:
    techs = analysis.get("technologies") or []
    security = analysis.get("security") or {}
    tls = analysis.get("tls") or {}
    email = analysis.get("email_security") or {}
    geo = analysis.get("geo") or {}
    domain = analysis.get("domain", "?")

    lines = [f"**Summary of `{domain}`**\n"]

    if techs:
        names = ", ".join(t.get("name", "?") for t in techs[:8])
        extra = f" (+{len(techs) - 8} more)" if len(techs) > 8 else ""
        lines.append(f"**Stack** ({len(techs)}): {names}{extra}")
    else:
        lines.append("**Stack**: no technologies detected.")

    if security.get("grade"):
        lines.append(f"**Security**: grade {security['grade']} — {len(security.get('findings') or [])} finding(s)")

    if tls.get("valid") is False:
        lines.append("**SSL**: invalid certificate")
    elif tls.get("issuer"):
        lines.append(f"**SSL**: valid ({tls['issuer']})")

    if email:
        flags = [
            f"SPF {'✓' if email.get('spf') else '✗'}",
            f"DMARC {'✓' if email.get('dmarc') else '✗'}",
            f"DNSSEC {'✓' if email.get('dnssec') else '✗'}",
        ]
        lines.append(f"**Email**: {' | '.join(flags)}")

    if geo.get("country"):
        loc = f"{geo['city']}, {geo['country']}" if geo.get("city") else geo["country"]
        lines.append(f"**Hosting**: {loc}" + (f" ({geo['isp']})" if geo.get("isp") else ""))

    errors = analysis.get("errors") or []
    if errors:
        failed = ", ".join(e.get("service", "?") for e in errors)
        lines.append(f"**Incomplete data**: these services failed during the analysis: {failed}")

    return "\n".join(lines)


# ── orquestador ───────────────────────────────────────────────────────────────

def get_ai_response(question: str, analysis: dict, history: list[dict]) -> dict:
    """Punto de entrada único.  Devuelve siempre un dict con answer/provider/status."""
    context = build_context(analysis)
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key and api_key.strip():
        try:
            answer = ask_gemini(question, context, history)
            return {"answer": answer, "provider": "gemini", "status": "success"}
        except Exception as exc:
            logger.warning("AI Chat: Gemini falló (%s), usando fallback local.", exc)
            return {"answer": ask_local(question, context, analysis), "provider": "local-fallback", "status": "success"}

    return {"answer": ask_local(question, context, analysis), "provider": "local", "status": "success"}
