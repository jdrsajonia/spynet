"""Tests del asistente de IA (funciones puras: contexto, resumen, fallback)."""
from api.ai_assistant import _MAX_CONTEXT_CHARS, build_context, _executive_summary, get_ai_response

SAMPLE = {
    "url": "https://example.com", "domain": "example.com", "status": "completed",
    "analyzed_at": "2026-07-13T10:00:00+00:00", "duration_ms": 4200, "triggered_by": "user",
    "technologies": [
        {"name": "React", "version": "18.2", "category": "frontend", "confidence": 90, "evidence": "html x"},
        {"name": "Nginx", "category": "server", "confidence": 60},
    ],
    "dns": {"A": ["1.2.3.4"], "NS": ["a.ns", "b.ns"], "TXT": ["v=spf1 -all"], "CAA": ["0 issue letsencrypt.org"]},
    "whois": {
        "registrar": "MarkMonitor", "country": "US", "domain_age_years": 25,
        "status": ["clientTransferProhibited https://icann.org/epp#x"],
        "emails": ["abuse@markmonitor.com"], "dnssec": "unsigned",
    },
    "geo": {"country": "US", "city": "LA", "isp": "Cloudflare", "ip": "1.2.3.4", "lat": 34.0, "lon": -118.2},
    "tls": {
        "valid": True, "issuer": "Sectigo", "tls_version": "TLSv1.3", "days_to_expiry": 80,
        "valid_from": "2026-01-01T00:00:00+00:00", "san": ["example.com", "*.example.com"],
    },
    "email_security": {"spf": "v=spf1 -all", "dmarc": None, "dnssec": False},
    "security": {
        "grade": "B", "score": 78,
        "findings": [{"severity": "medium", "category": "headers", "title": "Missing X-Content-Type-Options"}],
    },
    "wayback": {
        "snapshot_count": 2, "first_snapshot_at": "2001-05-01T00:00:00+00:00",
        "snapshots": [{"timestamp": "20010501120000", "technologies": [{"name": "jQuery"}]}],
    },
    "errors": [{"service": "whois", "code": "TIMEOUT", "message": "whois server did not respond"}],
}


def test_build_context_includes_key_sections():
    ctx = build_context(SAMPLE)
    assert "example.com" in ctx
    assert "Detected technologies (2)" in ctx
    assert "React v18.2" in ctx
    assert "DNS records" in ctx
    assert "SSL/TLS certificate" in ctx and "Sectigo" in ctx
    assert "Security audit: grade B" in ctx


def test_build_context_includes_late_added_card_data():
    """Todo lo que la vista Analyse pinta debe llegar al LLM (regresión)."""
    ctx = build_context(SAMPLE)
    # WHOIS: códigos EPP, emails de contacto y DNSSEC del registro
    assert "clientTransferProhibited" in ctx
    assert "abuse@markmonitor.com" in ctx
    assert "DNSSEC (registry): unsigned" in ctx
    # TLS: SAN y valid_from
    assert "example.com, *.example.com" in ctx
    assert "Valid from" in ctx
    # Geo: coordenadas
    assert "Latitude: 34.0" in ctx
    # DNS: tipos fuera de la lista corta y TXT completos
    assert "CAA:" in ctx
    assert "v=spf1 -all" in ctx
    # Seguridad: score y categoría del hallazgo
    assert "score 78/100" in ctx and "(headers)" in ctx
    # Wayback y fallos parciales
    assert "Wayback Machine history" in ctx and "jQuery" in ctx
    assert "whois: TIMEOUT" in ctx
    # Metadatos del análisis
    assert "Analyzed at" in ctx and "Triggered by" in ctx


def test_build_context_keeps_falsy_but_present_values():
    ctx = build_context({"url": "u", "domain": "d", "tls": {"valid": True, "days_to_expiry": 0}})
    assert "Days to expiry: 0" in ctx


def test_build_context_lists_missing_data():
    ctx = build_context({"url": "https://x.com", "domain": "x.com"})
    assert "Data NOT available" in ctx
    for name in ("technologies", "DNS", "WHOIS", "geolocation", "SSL/TLS", "Wayback history"):
        assert name in ctx


def test_build_context_truncates_long_input():
    big = dict(SAMPLE)
    big["technologies"] = [{"name": f"Tech{i}", "category": "x", "confidence": 50} for i in range(2000)]
    ctx = build_context(big)
    assert len(ctx) <= _MAX_CONTEXT_CHARS + 100      # límite + el sufijo de corte
    assert "truncated" in ctx
    # El recorte se come las tecnologías, no el final: la seguridad sobrevive.
    assert "Security audit: grade B" in ctx


def test_executive_summary_covers_stack_and_security():
    s = _executive_summary(SAMPLE)
    assert "example.com" in s
    assert "Stack" in s and "React" in s
    assert "grade B" in s
    assert "valid (Sectigo)" in s
    assert "SPF ✓" in s and "DMARC ✗" in s


def test_get_ai_response_falls_back_to_local_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    r = get_ai_response("summarize", SAMPLE, [])
    assert r["provider"] == "local"
    assert r["status"] == "success"
    assert r["answer"]
