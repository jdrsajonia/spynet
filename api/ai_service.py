"""
Servicio de IA para el chat del panel Analyse.

Sin dependencias de modelos Django — trabaja con dicts puros que llegan del
frontend.  Usa ``urllib.request`` (stdlib) para llamar a Gemini; si la clave
no está configurada o falla, devuelve una respuesta local basada en reglas.
"""

import json
import logging
import os
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

# Límites para no exceder tokens de Gemini ni enviar payloads enormes.
_MAX_CONTEXT_CHARS = 6000
_MAX_HISTORY_TURNS = 6  # últimos 6 mensajes (3 pares user/assistant)


# ── contexto textual ─────────────────────────────────────────────────────────

def _truncate(text: str, max_len: int = 300) -> str:
    """Trunca un texto largo con elipsis."""
    if not text or len(text) <= max_len:
        return text or ""
    return text[:max_len] + "…"


def build_context(analysis: dict) -> str:
    """Convierte el dict del análisis en un bloque de texto compacto para el LLM."""
    parts: list[str] = []

    parts.append(f"URL analizada: {analysis.get('url', '?')}")
    parts.append(f"Dominio: {analysis.get('domain', '?')}")
    parts.append(f"Estado del análisis: {analysis.get('status', '?')}")

    if analysis.get("duration_ms"):
        parts.append(f"Duración del análisis: {analysis['duration_ms']}ms")

    # Tecnologías
    techs = analysis.get("technologies") or []
    if techs:
        items = []
        for t in techs:
            entry = t.get("name", "?")
            if t.get("version"):
                entry += f" v{t['version']}"
            cat = t.get("category", "?")
            conf = t.get("confidence", "?")
            evidence = _truncate(t.get("evidence", ""), 150)
            entry += f" (categoría: {cat}, confianza: {conf}%)"
            if evidence:
                entry += f" [evidencia: {evidence}]"
            items.append(entry)
        parts.append(f"Tecnologías detectadas ({len(techs)}):\n" + "\n".join(f"  - {i}" for i in items))
    else:
        parts.append("Tecnologías detectadas: ninguna")

    # DNS
    dns = analysis.get("dns") or {}
    dns_lines = []
    for rtype in ("A", "AAAA", "CNAME", "NS", "MX"):
        vals = dns.get(rtype)
        if vals:
            dns_lines.append(f"  {rtype}: {', '.join(str(v) for v in vals[:10])}")
    txt_records = dns.get("TXT") or []
    if txt_records:
        # Solo los primeros 5 TXT, truncados
        for txt in txt_records[:5]:
            dns_lines.append(f"  TXT: {_truncate(str(txt), 200)}")
        if len(txt_records) > 5:
            dns_lines.append(f"  (+{len(txt_records) - 5} registros TXT más)")
    if dns_lines:
        parts.append("Registros DNS:\n" + "\n".join(dns_lines))

    # WHOIS
    whois = analysis.get("whois") or {}
    whois_items = []
    for key, label in [("registrar", "Registrador"), ("org", "Organización"),
                        ("registrant", "Registrante"), ("country", "País"),
                        ("creation_date", "Fecha creación"), ("expiration_date", "Fecha expiración"),
                        ("updated_date", "Última actualización"), ("domain_age_years", "Antigüedad (años)")]:
        val = whois.get(key)
        if val:
            whois_items.append(f"  {label}: {val}")
    status = whois.get("status") or []
    if status:
        whois_items.append(f"  Estado: {', '.join(str(s).split()[0] for s in status[:5])}")
    if whois_items:
        parts.append("WHOIS:\n" + "\n".join(whois_items))

    # Geo
    geo = analysis.get("geo") or {}
    geo_items = []
    for key, label in [("country", "País"), ("city", "Ciudad"), ("isp", "ISP"),
                        ("org", "Organización"), ("ip", "IP"), ("reverse_dns", "Reverse DNS")]:
        val = geo.get(key)
        if val:
            geo_items.append(f"  {label}: {val}")
    if geo.get("lat") and geo.get("lon"):
        geo_items.append(f"  Coordenadas: {geo['lat']}, {geo['lon']}")
    if geo_items:
        parts.append("Geolocalización:\n" + "\n".join(geo_items))

    # TLS
    tls = analysis.get("tls") or {}
    if tls:
        tls_items = []
        if tls.get("valid") is True:
            tls_items.append("  Estado: Válido ✓")
        elif tls.get("valid") is False:
            tls_items.append(f"  Estado: INVÁLIDO ({tls.get('error', 'error desconocido')})")
        for key, label in [("issuer", "Emisor"), ("subject_cn", "Common Name"),
                            ("valid_to", "Válido hasta"), ("tls_version", "Versión TLS")]:
            val = tls.get(key)
            if val:
                tls_items.append(f"  {label}: {val}")
        if tls.get("days_to_expiry") is not None:
            tls_items.append(f"  Días para expirar: {tls['days_to_expiry']}")
        san = tls.get("san") or []
        if san:
            tls_items.append(f"  SANs: {', '.join(san[:5])}" + (f" (+{len(san)-5} más)" if len(san) > 5 else ""))
        if tls_items:
            parts.append("Certificado SSL/TLS:\n" + "\n".join(tls_items))

    # Email security
    email = analysis.get("email_security") or {}
    if email:
        email_items = []
        if email.get("spf"):
            email_items.append(f"  SPF: {_truncate(email['spf'], 200)}")
        else:
            email_items.append("  SPF: No configurado")
        if email.get("dmarc"):
            email_items.append(f"  DMARC: {_truncate(email['dmarc'], 200)}")
        else:
            email_items.append("  DMARC: No configurado")
        email_items.append(f"  DNSSEC: {'Habilitado' if email.get('dnssec') else 'No habilitado'}")
        parts.append("Seguridad de email:\n" + "\n".join(email_items))

    # Security audit
    security = analysis.get("security") or {}
    if security:
        grade = security.get("grade", "?")
        findings = security.get("findings") or []
        parts.append(f"Auditoría de seguridad: Grado {grade}, {len(findings)} hallazgo(s)")
        for f in findings[:12]:
            sev = f.get("severity", "?")
            title = f.get("title", "?")
            detail = _truncate(f.get("detail", ""), 200)
            tech = f.get("tech", "")
            cat = f.get("category", "")
            line = f"  [{sev.upper()}] {title}"
            if tech:
                line += f" ({tech})"
            if cat:
                line += f" [{cat}]"
            if detail:
                line += f": {detail}"
            parts.append(line)

    # Headers de respuesta HTTP (si están disponibles)
    headers = analysis.get("headers") or {}
    if headers:
        security_headers = ["X-Frame-Options", "Content-Security-Policy",
                           "X-Content-Type-Options", "Strict-Transport-Security",
                           "X-XSS-Protection", "Referrer-Policy", "Permissions-Policy"]
        h_items = []
        for h in security_headers:
            val = headers.get(h) or headers.get(h.lower())
            if val:
                h_items.append(f"  {h}: {_truncate(str(val), 150)}")
        if h_items:
            parts.append("Headers de seguridad HTTP:\n" + "\n".join(h_items))

    # Información que NO está disponible (para que el LLM no invente)
    missing = []
    if not techs:
        missing.append("tecnologías")
    if not dns:
        missing.append("DNS")
    if not whois:
        missing.append("WHOIS")
    if not geo:
        missing.append("geolocalización")
    if not tls:
        missing.append("SSL/TLS")
    if missing:
        parts.append(f"Datos no disponibles en este análisis: {', '.join(missing)}")

    context = "\n".join(parts)
    # Truncar contexto total si es muy largo
    if len(context) > _MAX_CONTEXT_CHARS:
        context = context[:_MAX_CONTEXT_CHARS] + "\n[contexto truncado por longitud]"
    return context


# ── Gemini (REST, stdlib) ─────────────────────────────────────────────────────

_GEMINI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)

_DEFAULT_MODEL = "gemini-2.5-flash"

_SYSTEM_PROMPT = """\
Eres el asistente experto de SpyNet, una plataforma de inteligencia web.
Tu rol es ayudar al usuario a entender el análisis técnico de una página web y convertirlo en acciones claras.
Hablas como un consultor senior en tecnología web, arquitectura, ciberseguridad, SEO técnico, analítica, performance y experiencia de usuario.

ESTILO:
- Natural y conversacional, como un colega experto.
- Claro, directo, profesional pero fácil de entender.
- Específico al sitio analizado — no genérico.
- Orientado a acciones concretas.
- Sin sonar robótico.
- Sin repetir todo el análisis si no se pide.
- Sin inventar datos que no estén en el contexto.
- Sin frases genéricas vacías ni relleno.
- Sin alarmismo innecesario.
- Responder en el mismo idioma que usa el usuario.
- Explicar conceptos técnicos en lenguaje simple.
- Priorizar lo más importante primero.

REGLAS DE FORMATO Y CONTENIDO:
- Responde en Markdown limpio.
- Usa títulos cortos, bullets claros y párrafos breves.
- No uses tablas salvo que el usuario las pida explícitamente.
- Usa código inline con backticks SOLO para nombres técnicos específicos como headers, directivas, cabeceras HTTP o valores exactos (ej. `Strict-Transport-Security`, `DENY`, `SAMEORIGIN`, `includeSubDomains`).
- No envuelvas palabras comunes ni frases enteras en backticks.
- Evita listas demasiado anidadas.
- No responder como JSON ni decir "según el contexto proporcionado".
- Si algo no está en el análisis, decirlo claramente.
- Cuando el usuario pida mejoras o recomendaciones, usa secciones simples y claras:
  1. Diagnóstico rápido (qué se observa).
  2. Acciones prioritarias (qué hacer primero).
  3. Impacto esperado (por qué importa).
  4. Siguiente paso recomendado.
- Cuando pida riesgos, separa prioridad, impacto y recomendación.
- Cuando pida resumen, da un resumen ejecutivo corto.
- Menciona puntos positivos cuando los haya (SSL válido, analytics presente, etc.).
- No usar más de 500 palabras salvo que el usuario pida detalle."""


def ask_gemini(question: str, context: str, history: list[dict]) -> str:
    """Llama a Gemini REST API.  Lanza excepción si falla."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError("GEMINI_API_KEY no configurada")
    api_key = api_key.strip()

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not model or not model.strip():
        model = "gemini-2.5-flash"
    else:
        model = model.strip()

    # Armar contents con contexto, historial reciente y pregunta
    contents: list[dict] = []

    # Contexto como primer intercambio
    contents.append({
        "role": "user",
        "parts": [{"text": f"[CONTEXTO DEL ANÁLISIS WEB]\n{context}"}],
    })
    contents.append({
        "role": "model",
        "parts": [{"text": "Entendido. Tengo el análisis completo del sitio. ¿En qué te puedo ayudar?"}],
    })

    # Historial previo (limitado a los últimos _MAX_HISTORY_TURNS)
    recent_history = (history or [])[-_MAX_HISTORY_TURNS:]
    for msg in recent_history:
        role = "model" if msg.get("role") == "assistant" else "user"
        text = msg.get("content", "")
        if text:
            contents.append({"role": role, "parts": [{"text": text}]})

    # Pregunta actual
    contents.append({"role": "user", "parts": [{"text": question}]})

    payload = json.dumps({
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.75,
            "maxOutputTokens": 2048,
        },
    }).encode()

    url = _GEMINI_BASE_URL.format(model=model, key=api_key)
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()[:500]
        except Exception:
            pass
        if e.code == 401 or e.code == 403:
            logger.error("Gemini: error de autenticación (HTTP %d). Verifica GEMINI_API_KEY.", e.code)
            raise RuntimeError(f"Gemini auth error (HTTP {e.code})")
        elif e.code == 429:
            logger.warning("Gemini: rate limit alcanzado (HTTP 429).")
            raise RuntimeError("Gemini rate limit (HTTP 429)")
        elif e.code >= 500:
            logger.warning("Gemini: error del servidor (HTTP %d).", e.code)
            raise RuntimeError(f"Gemini server error (HTTP {e.code})")
        else:
            logger.warning("Gemini: HTTP %d — %s", e.code, error_body[:200])
            raise RuntimeError(f"Gemini HTTP {e.code}")
    except urllib.error.URLError as e:
        logger.warning("Gemini: error de red — %s", e.reason)
        raise RuntimeError(f"Gemini network error: {e.reason}")
    except TimeoutError:
        logger.warning("Gemini: timeout tras 30s.")
        raise RuntimeError("Gemini timeout")

    # Extraer texto de la respuesta
    candidates = body.get("candidates") or []
    if not candidates:
        logger.warning("Gemini: respuesta sin candidatos — %s", json.dumps(body)[:300])
        raise RuntimeError("Gemini: respuesta vacía (sin candidatos)")

    parts = candidates[0].get("content", {}).get("parts") or []
    answer = parts[0].get("text", "") if parts else ""

    if not answer.strip():
        logger.warning("Gemini: respuesta con texto vacío.")
        raise RuntimeError("Gemini: respuesta con texto vacío")

    return answer


# ── fallback local avanzado ───────────────────────────────────────────────────

def ask_local(question: str, context: str, analysis: dict) -> str:
    """Genera una respuesta consultiva basada en reglas usando los datos reales."""
    q = question.lower()
    techs = analysis.get("technologies") or []
    dns = analysis.get("dns") or {}
    whois = analysis.get("whois") or {}
    geo = analysis.get("geo") or {}
    tls = analysis.get("tls") or {}
    security = analysis.get("security") or {}
    email = analysis.get("email_security") or {}
    url = analysis.get("url", "desconocida")
    domain = analysis.get("domain", "desconocido")
    tech_names = [t.get("name", "") for t in techs]

    # ── mejoras / recomendaciones / optimizar ─────────────────────────────
    if any(kw in q for kw in ("mejor", "optimi", "recomend", "qué hago", "qué debo",
                               "next step", "improve", "optimize", "plan de acción",
                               "action plan", "cómo mejoro", "como mejoro")):
        return _build_recommendations(analysis, techs, security, email, tls, geo, url, domain, tech_names)

    # ── tecnologías / stack ───────────────────────────────────────────────
    if any(kw in q for kw in ("tecnolog", "tech", "stack")):
        if not techs:
            return f"No se detectaron tecnologías en {url}."
        lines = [f"El análisis detectó **{len(techs)} tecnologías** en `{domain}`:"]
        # Agrupar por categoría
        cats: dict[str, list] = {}
        for t in techs:
            cat = t.get("category", "Otro")
            cats.setdefault(cat, []).append(t)
        for cat, items in sorted(cats.items()):
            lines.append(f"\n**{cat.replace('-', ' ').title()}:**")
            for t in items:
                ver = f" v{t['version']}" if t.get("version") else ""
                lines.append(f"• {t['name']}{ver} ({t.get('confidence', '?')}% confianza)")
        return "\n".join(lines)

    # ── framework / CMS ───────────────────────────────────────────────────
    if any(kw in q for kw in ("framework", "cms", "librería", "library")):
        fw = [t for t in techs if any(k in t.get("category", "").lower()
              for k in ("framework", "cms", "library"))]
        if fw:
            lines = ["Frameworks y librerías detectados:"]
            for t in fw:
                ver = f" v{t['version']}" if t.get("version") else ""
                lines.append(f"• **{t['name']}{ver}** — {t.get('category', '?')}")
            return "\n".join(lines)
        return "No se detectaron frameworks o CMS específicos. El sitio podría usar HTML estático o un stack que no dejó huellas detectables."

    # ── seguridad / riesgos ───────────────────────────────────────────────
    if any(kw in q for kw in ("riesgo", "risk", "débil", "vulnerab", "seguridad",
                               "security", "problema", "prioriz")):
        return _build_security_response(security, tls, email, domain, tech_names)

    # ── DNS ────────────────────────────────────────────────────────────────
    if "dns" in q:
        if not dns:
            return f"No se obtuvieron registros DNS para {domain}."
        lines = [f"Registros DNS de **{domain}**:"]
        for rtype in ("A", "AAAA", "CNAME", "NS", "MX"):
            vals = dns.get(rtype)
            if vals:
                lines.append(f"• **{rtype}**: {', '.join(str(v) for v in vals[:8])}")
        txt = dns.get("TXT") or []
        if txt:
            lines.append(f"• **TXT**: {len(txt)} registro(s)")
            # Resaltar registros importantes
            for t in txt[:3]:
                ts = str(t)
                if any(k in ts.lower() for k in ("spf", "dmarc", "google", "facebook", "v=")):
                    lines.append(f"  → `{_truncate(ts, 120)}`")
        lines.append(f"\nLos registros DNS muestran la infraestructura del dominio. "
                     f"Los NS indican quién hospeda el DNS, los A/AAAA apuntan al servidor, "
                     f"y los TXT suelen contener verificaciones de servicios y políticas de email.")
        return "\n".join(lines)

    # ── WHOIS ──────────────────────────────────────────────────────────────
    if any(kw in q for kw in ("whois", "registr")):
        if not whois:
            return f"No se obtuvieron datos WHOIS para {domain}."
        lines = [f"Datos de registro del dominio **{domain}**:"]
        mapping = {
            "registrar": "Registrador", "org": "Organización", "country": "País",
            "creation_date": "Creado", "expiration_date": "Expira",
            "domain_age_years": "Antigüedad",
        }
        for key, label in mapping.items():
            val = whois.get(key)
            if val:
                suffix = " años" if key == "domain_age_years" else ""
                lines.append(f"• **{label}**: {val}{suffix}")
        age = whois.get("domain_age_years")
        if age:
            if age < 1:
                lines.append("\n⚠️ Dominio muy nuevo (menos de 1 año). Esto puede afectar la confianza y el SEO.")
            elif age > 10:
                lines.append(f"\n✅ Dominio con {age} años de antigüedad — buena señal de estabilidad y confianza.")
        return "\n".join(lines)

    # ── Geo ─────────────────────────────────────────────────────────────────
    if any(kw in q for kw in ("geo", "ubicaci", "localiz", "país", "ciudad", "isp", "servidor")):
        if not geo:
            return f"No se obtuvo información de geolocalización para {domain}."
        lines = [f"Ubicación del servidor de **{domain}**:"]
        if geo.get("country"):
            lines.append(f"• **País**: {geo['country']}")
        if geo.get("city"):
            lines.append(f"• **Ciudad**: {geo['city']}")
        if geo.get("isp"):
            lines.append(f"• **ISP / Hosting**: {geo['isp']}")
        if geo.get("org"):
            lines.append(f"• **Organización**: {geo['org']}")
        if geo.get("ip"):
            lines.append(f"• **IP**: {geo['ip']}")
        if geo.get("isp"):
            isp = geo["isp"].lower()
            if any(cloud in isp for cloud in ("amazon", "aws", "cloudflare", "google", "azure", "digitalocean")):
                lines.append(f"\nEl sitio está alojado en infraestructura cloud ({geo['isp']}), lo que suele indicar buen rendimiento y escalabilidad.")
        return "\n".join(lines)

    # ── TLS/SSL ────────────────────────────────────────────────────────────
    if any(kw in q for kw in ("ssl", "tls", "certificado", "https")):
        if not tls:
            return "No se obtuvo información del certificado SSL. Esto podría significar que el sitio no usa HTTPS."
        lines = ["**Certificado SSL/TLS:**"]
        if tls.get("valid") is False:
            lines.append(f"⚠️ **Certificado inválido**: {tls.get('error', 'error desconocido')}")
            lines.append("Esto genera alertas en navegadores y afecta confianza y SEO.")
        else:
            lines.append("✅ Certificado válido")
        if tls.get("issuer"):
            lines.append(f"• **Emisor**: {tls['issuer']}")
        if tls.get("subject_cn"):
            lines.append(f"• **Common Name**: {tls['subject_cn']}")
        if tls.get("valid_to"):
            lines.append(f"• **Válido hasta**: {tls['valid_to']}")
            days = tls.get("days_to_expiry")
            if days is not None and days < 30:
                lines.append(f"  ⚠️ Expira en {days} días — renovar pronto.")
        if tls.get("tls_version"):
            lines.append(f"• **Versión**: {tls['tls_version']}")
        return "\n".join(lines)

    # ── resumen ────────────────────────────────────────────────────────────
    if any(kw in q for kw in ("resum", "general", "describe", "explica", "qué es",
                               "analisis", "análisis", "summary", "overview")):
        return _build_executive_summary(analysis, techs, security, email, tls, geo, domain, url)

    # ── SEO / performance ─────────────────────────────────────────────────
    if any(kw in q for kw in ("seo", "performance", "rendimiento", "velocidad",
                               "google", "posicionamiento")):
        return _build_seo_response(techs, tls, email, security, domain, tech_names)

    # Default → resumen ejecutivo
    return _build_executive_summary(analysis, techs, security, email, tls, geo, domain, url)


def _build_recommendations(analysis, techs, security, email, tls, geo, url, domain, tech_names):
    """Respuesta consultiva de mejoras priorizadas."""
    lines = [f"**Diagnóstico rápido de `{domain}`:**\n"]

    # Positivos
    positives = []
    if tls and tls.get("valid") is not False:
        positives.append("SSL válido")
    analytics = [n for n in tech_names if any(k in n.lower() for k in ("analytics", "tag manager", "gtm", "matomo"))]
    if analytics:
        positives.append(f"herramientas de medición ({', '.join(analytics)})")
    if len(techs) > 3:
        positives.append(f"{len(techs)} tecnologías detectadas")
    if positives:
        lines.append(f"✅ Puntos positivos: {', '.join(positives)}.\n")

    # Acciones prioritarias
    lines.append("**Acciones prioritarias:**\n")
    priority = 1

    findings = (security.get("findings") or [])
    high_findings = [f for f in findings if f.get("severity") == "high"]
    medium_findings = [f for f in findings if f.get("severity") == "medium"]

    if high_findings:
        lines.append(f"{priority}. **Resolver hallazgos de seguridad críticos** ({len(high_findings)} de severidad alta)")
        for f in high_findings[:3]:
            lines.append(f"   • {f.get('title', '?')}")
        lines.append(f"   → Impacto: protege al sitio y sus usuarios de vulnerabilidades activas.\n")
        priority += 1

    if not email.get("dmarc"):
        lines.append(f"{priority}. **Configurar DMARC** para proteger el dominio contra suplantación de email (spoofing).")
        lines.append(f"   → Es un cambio rápido en DNS con impacto alto en seguridad.\n")
        priority += 1

    if not email.get("spf"):
        lines.append(f"{priority}. **Agregar registro SPF** para validar qué servidores pueden enviar email desde {domain}.")
        lines.append(f"   → Previene que terceros envíen correo haciéndose pasar por tu dominio.\n")
        priority += 1

    if medium_findings:
        lines.append(f"{priority}. **Atender hallazgos de seguridad media** ({len(medium_findings)})")
        for f in medium_findings[:3]:
            lines.append(f"   • {f.get('title', '?')}")
        lines.append("")
        priority += 1

    if tls and tls.get("valid") is False:
        lines.append(f"{priority}. **Corregir el certificado SSL** — un certificado inválido genera alertas en navegadores y afecta SEO.")
        lines.append("")
        priority += 1

    outdated = [f for f in findings if f.get("category") == "outdated"]
    if outdated:
        lines.append(f"{priority}. **Actualizar tecnologías obsoletas**: {', '.join(set(f.get('tech', '?') for f in outdated))}")
        lines.append("   → Las versiones EOL no reciben parches de seguridad.\n")
        priority += 1

    if not analytics:
        lines.append(f"{priority}. **Implementar analítica web** (Google Analytics, Matomo, etc.) para medir tráfico y comportamiento de usuarios.")
        lines.append("   → Sin medición, no puedes optimizar basándote en datos reales.\n")
        priority += 1

    if priority == 1:
        lines.append("El sitio se ve bien configurado. No se detectaron problemas críticos.")
        lines.append("Para ir más allá, considera una auditoría de performance (Lighthouse) y de SEO (Search Console).\n")

    lines.append("**Siguiente paso:** Lo más rentable sería empezar por el punto 1 de la lista, que es el de mayor impacto inmediato.")

    return "\n".join(lines)


def _build_security_response(security, tls, email, domain, tech_names):
    """Respuesta detallada de seguridad."""
    findings = security.get("findings") or []
    grade = security.get("grade", "?")

    lines = [f"**Análisis de seguridad de `{domain}`:**\n"]
    lines.append(f"Grado: **{grade}** — {len(findings)} hallazgo(s)\n")

    if not findings and (tls and tls.get("valid") is not False):
        lines.append("✅ No se detectaron problemas de seguridad significativos. Buen estado general.")
        if email.get("dmarc") and email.get("spf"):
            lines.append("✅ Email security configurado (SPF + DMARC).")
        return "\n".join(lines)

    # Agrupar por severidad
    by_sev: dict[str, list] = {}
    for f in findings:
        sev = f.get("severity", "info")
        by_sev.setdefault(sev, []).append(f)

    sev_order = ["high", "medium", "low", "info"]
    sev_labels = {"high": "🔴 Alta", "medium": "🟡 Media", "low": "🔵 Baja", "info": "ℹ️ Info"}

    for sev in sev_order:
        items = by_sev.get(sev, [])
        if items:
            lines.append(f"**{sev_labels.get(sev, sev)}** ({len(items)}):")
            for f in items:
                lines.append(f"• **{f.get('title', '?')}**")
                if f.get("detail"):
                    lines.append(f"  {_truncate(f['detail'], 150)}")
            lines.append("")

    # Email security
    email_issues = []
    if not email.get("spf"):
        email_issues.append("SPF no configurado")
    if not email.get("dmarc"):
        email_issues.append("DMARC no configurado")
    if not email.get("dnssec"):
        email_issues.append("DNSSEC no habilitado")
    if email_issues:
        lines.append("**Seguridad de email:**")
        for issue in email_issues:
            lines.append(f"• ⚠️ {issue}")
        lines.append("")

    if tls and tls.get("valid") is False:
        lines.append(f"**SSL:** ⚠️ Certificado inválido — {tls.get('error', 'error desconocido')}")

    lines.append("**Recomendación:** Prioriza primero los hallazgos de severidad alta, luego configura SPF/DMARC si no lo tienes, y después atiende los de severidad media.")
    return "\n".join(lines)


def _build_seo_response(techs, tls, email, security, domain, tech_names):
    """Respuesta sobre SEO y performance."""
    lines = [f"**SEO técnico y performance de `{domain}`:**\n"]
    lines.append("_Nota: SpyNet analiza la infraestructura técnica, no el contenido ni PageSpeed. Estas son observaciones basadas en lo detectado:_\n")

    # SSL
    if tls and tls.get("valid") is not False:
        lines.append("✅ **HTTPS habilitado** — fundamental para SEO (Google lo usa como factor de ranking).")
    elif tls and tls.get("valid") is False:
        lines.append("⚠️ **SSL inválido** — Google penaliza sitios sin HTTPS válido en los resultados de búsqueda.")
    else:
        lines.append("⚠️ **Sin datos de SSL** — verifica que el sitio use HTTPS.")

    # Analytics
    analytics = [n for n in tech_names if any(k in n.lower() for k in ("analytics", "tag manager", "gtm", "matomo", "plausible"))]
    if analytics:
        lines.append(f"✅ **Analítica activa**: {', '.join(analytics)} — puedes medir tráfico y comportamiento.")
    else:
        lines.append("⚠️ **Sin herramienta de analítica detectada** — sin datos no puedes optimizar. Implementa Google Analytics o similar.")

    # Frameworks y rendimiento
    heavy = [n for n in tech_names if any(k in n.lower() for k in ("jquery", "bootstrap", "wordpress"))]
    modern = [n for n in tech_names if any(k in n.lower() for k in ("react", "next", "vue", "nuxt", "svelte", "angular"))]
    if modern:
        lines.append(f"✅ **Framework moderno**: {', '.join(modern)} — generalmente bueno para performance y SEO.")
    if heavy:
        lines.append(f"ℹ️ **Tecnologías pesadas detectadas**: {', '.join(heavy)} — pueden impactar el tiempo de carga si no se optimizan.")

    # Email (afecta entregabilidad, indirectamente SEO de marca)
    if not email.get("dmarc") or not email.get("spf"):
        lines.append("⚠️ **Email security incompleto** (SPF/DMARC) — no afecta directamente al SEO, pero protege la reputación del dominio.")

    lines.append("\n**Recomendación:** Complementa este análisis con Google PageSpeed Insights y Google Search Console para una vista completa de SEO y performance.")
    return "\n".join(lines)


def _build_executive_summary(analysis, techs, security, email, tls, geo, domain, url):
    """Resumen ejecutivo del análisis."""
    lines = [f"**Resumen ejecutivo del análisis de `{domain}`:**\n"]

    # Stack tecnológico
    if techs:
        top_names = [t.get("name", "?") for t in techs[:8]]
        lines.append(f"**Stack tecnológico** ({len(techs)} tecnologías): {', '.join(top_names)}")
        if len(techs) > 8:
            lines.append(f"  (+{len(techs) - 8} más)")
    else:
        lines.append("**Stack tecnológico**: No se detectaron tecnologías.")

    # Seguridad
    grade = security.get("grade")
    findings = security.get("findings") or []
    if grade:
        high = len([f for f in findings if f.get("severity") == "high"])
        lines.append(f"\n**Seguridad**: Grado **{grade}** — {len(findings)} hallazgo(s)" +
                     (f", {high} de severidad alta" if high else ""))

    # SSL
    if tls:
        if tls.get("valid") is False:
            lines.append("**SSL**: ⚠️ Certificado inválido")
        elif tls.get("issuer"):
            lines.append(f"**SSL**: ✅ Válido ({tls['issuer']})")

    # Email
    if email:
        status_parts = []
        status_parts.append("SPF ✓" if email.get("spf") else "SPF ✗")
        status_parts.append("DMARC ✓" if email.get("dmarc") else "DMARC ✗")
        status_parts.append("DNSSEC ✓" if email.get("dnssec") else "DNSSEC ✗")
        lines.append(f"**Email**: {' | '.join(status_parts)}")

    # Hosting
    if geo.get("country"):
        loc = geo["country"]
        if geo.get("city"):
            loc = f"{geo['city']}, {loc}"
        isp = geo.get("isp", "?")
        lines.append(f"**Hosting**: {loc} ({isp})")

    return "\n".join(lines)


# ── orquestador ───────────────────────────────────────────────────────────────

def get_ai_response(question: str, analysis: dict, history: list[dict]) -> dict:
    """Punto de entrada único.  Devuelve siempre un dict con answer/provider/status."""
    context = build_context(analysis)

    # Intentar Gemini si la clave está configurada
    api_key = os.getenv("GEMINI_API_KEY")

    if api_key and api_key.strip():
        logger.info("AI Chat: GEMINI_API_KEY presente, intentando Gemini...")
        try:
            answer = ask_gemini(question, context, history)
            logger.info("AI Chat: respuesta exitosa via Gemini (provider=gemini).")
            return {"answer": answer, "provider": "gemini", "status": "success"}
        except Exception as exc:
            logger.warning("AI Chat: Gemini falló (%s), cayendo a fallback local.", exc)
            answer = ask_local(question, context, analysis)
            return {"answer": answer, "provider": "local-fallback", "status": "success"}
    else:
        logger.info("AI Chat: GEMINI_API_KEY no configurada, usando fallback local (provider=local).")
        answer = ask_local(question, context, analysis)
        return {"answer": answer, "provider": "local", "status": "success"}
