"""
Auditoría de seguridad PASIVA sobre datos que el análisis ya capturó (headers,
cookies, versiones, certificado TLS y postura de correo/DNS). No hace red extra.

La nota A–F NO es un veredicto de "qué tan hackeable es el sitio": es una postura
de buenas prácticas de seguridad. El puntaje se arma con comprobaciones ponderadas
que SUMAN cuando se cumplen (premia lo bueno: HTTPS válido, HSTS, DMARC, DNSSEC,
sin software EOL…), no solo restan por lo que falta. Así un sitio bien configurado
(ej. Google) obtiene buena nota aunque le falte algún header "nice-to-have".

Se reconoce `Content-Security-Policy-Report-Only` como CSP presente (es una forma
legítima de desplegar CSP que usan muchos sitios grandes).
"""

# Versión mínima CON SOPORTE por tecnología. Si la detectada es menor → EOL.
_EOL_MIN_SUPPORTED = {
    "PHP":           "8.1",
    "jQuery":        "3.0",
    "Bootstrap":     "5.0",
    "Nginx":         "1.24",
    "Apache":        "2.4",
    "OpenSSL":       "3.0",
    "WordPress":     "6.0",
    "Microsoft IIS": "10.0",
}

# Headers que filtran versión/tecnología (information disclosure).
_DISCLOSURE_HEADERS = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator"]

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def audit(headers: dict, cookies: list | None, technologies: list | None,
          tls: dict | None = None, email: dict | None = None) -> dict:
    """Devuelve { grade, score, findings: [ {category, severity, title, detail, tech?} ] }."""
    hdrs = {k.lower(): v for k, v in (headers or {}).items()}
    email = email or {}

    def has(header: str) -> bool:
        return header in hdrs

    # CSP: se acepta también el modo report-only (despliegue legítimo).
    csp_ok = has("content-security-policy") or has("content-security-policy-report-only")

    # Hallazgos detallados; además determinan tres de las comprobaciones.
    eol_findings = _eol_findings(technologies)
    cookie_findings = _cookie_findings(cookies)
    disclosure_findings = _disclosure_findings(hdrs)

    # Comprobaciones ponderadas: (peso, severidad, se_cumple, título-si-falla, categoría).
    # Las de título None ya aportan su detalle vía los *_findings de arriba.
    checks = [
        (18, "high",   bool(tls and tls.get("valid") is True), "Sin HTTPS con certificado válido",        "infra"),
        (14, "high",   has("strict-transport-security"),       "Falta HSTS (Strict-Transport-Security)",  "headers"),
        (12, "high",   csp_ok,                                  "Falta Content-Security-Policy",           "headers"),
        (12, "high",   not eol_findings,                        None,                                       None),
        (8,  "medium", has("x-frame-options"),                  "Falta X-Frame-Options",                    "headers"),
        (8,  "medium", bool(email.get("dmarc")),                "Sin política DMARC de correo",             "infra"),
        (6,  "medium", has("x-content-type-options"),           "Falta X-Content-Type-Options",             "headers"),
        (5,  "medium", not cookie_findings,                     None,                                       None),
        (5,  "low",    bool(email.get("dnssec")),               "Sin DNSSEC",                               "infra"),
        (4,  "low",    has("referrer-policy"),                  "Falta Referrer-Policy",                    "headers"),
        (4,  "low",    has("permissions-policy"),               "Falta Permissions-Policy",                 "headers"),
        (4,  "low",    not disclosure_findings,                 None,                                       None),
    ]

    earned = sum(w for (w, _, ok, _, _) in checks if ok)
    total = sum(w for (w, _, _, _, _) in checks)
    score = round(earned / total * 100) if total else 100

    findings = list(eol_findings) + list(cookie_findings) + list(disclosure_findings)
    for (_, severity, ok, title, category) in checks:
        if not ok and title:
            findings.append({
                "category": category, "severity": severity,
                "title": title, "detail": "Práctica de seguridad recomendada ausente.",
            })
    findings.sort(key=lambda f: _SEVERITY_ORDER.get(f["severity"], 3))

    return {"grade": _grade(score), "score": score, "findings": findings}


def _eol_findings(technologies: list | None) -> list[dict]:
    out = []
    for tech in (technologies or []):
        min_ver = _EOL_MIN_SUPPORTED.get(tech.get("name"))
        version = tech.get("version")
        if min_ver and version and _is_older(version, min_ver):
            out.append({
                "category": "outdated", "severity": "high",
                "title": f"{tech['name']} {version} está sin soporte (EOL)",
                "detail": f"Versión mínima con soporte: {min_ver}.",
                "tech": tech["name"],
            })
    return out


def _cookie_findings(cookies: list | None) -> list[dict]:
    out = []
    for cookie in (cookies or []):
        missing = []
        if not cookie.get("secure"):   missing.append("Secure")
        if not cookie.get("httponly"): missing.append("HttpOnly")
        if not cookie.get("samesite"): missing.append("SameSite")
        if missing:
            out.append({
                "category": "cookies", "severity": "medium",
                "title": f"Cookie '{cookie.get('name')}' sin {', '.join(missing)}",
                "detail": "Flags de seguridad recomendados ausentes.",
            })
    return out


def _disclosure_findings(hdrs: dict) -> list[dict]:
    out = []
    for key in _DISCLOSURE_HEADERS:
        value = hdrs.get(key)
        if value and any(ch.isdigit() for ch in value):
            out.append({
                "category": "disclosure", "severity": "low",
                "title": f"El header '{key}' revela versión",
                "detail": value,
            })
    return out


def _grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 75: return "B"
    if score >= 60: return "C"
    if score >= 40: return "D"
    return "F"


def _is_older(version: str, minimum: str) -> bool:
    return _version_tuple(version) < _version_tuple(minimum)


def _version_tuple(version: str) -> tuple:
    parts = []
    for chunk in str(version).split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)
