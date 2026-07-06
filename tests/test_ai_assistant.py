"""Tests del asistente de IA (funciones puras: contexto, resumen, fallback)."""
from api.ai_assistant import build_context, _executive_summary, get_ai_response

SAMPLE = {
    "url": "https://example.com", "domain": "example.com", "status": "completed",
    "technologies": [
        {"name": "React", "version": "18.2", "category": "frontend", "confidence": 90, "evidence": "html x"},
        {"name": "Nginx", "category": "server", "confidence": 60},
    ],
    "dns": {"A": ["1.2.3.4"], "NS": ["a.ns", "b.ns"], "TXT": ["v=spf1 -all"]},
    "whois": {"registrar": "MarkMonitor", "country": "US", "domain_age_years": 25},
    "geo": {"country": "US", "city": "LA", "isp": "Cloudflare", "ip": "1.2.3.4"},
    "tls": {"valid": True, "issuer": "Sectigo", "tls_version": "TLSv1.3", "days_to_expiry": 80},
    "email_security": {"spf": "v=spf1 -all", "dmarc": None, "dnssec": False},
    "security": {"grade": "B", "findings": [{"severity": "medium", "title": "Missing X-Content-Type-Options"}]},
}


def test_build_context_includes_key_sections():
    ctx = build_context(SAMPLE)
    assert "example.com" in ctx
    assert "Detected technologies (2)" in ctx
    assert "React v18.2" in ctx
    assert "DNS records" in ctx
    assert "SSL/TLS certificate" in ctx and "Sectigo" in ctx
    assert "Security audit: grade B" in ctx


def test_build_context_lists_missing_data():
    ctx = build_context({"url": "https://x.com", "domain": "x.com"})
    assert "Data NOT available" in ctx
    for name in ("technologies", "DNS", "WHOIS", "geolocation", "SSL/TLS"):
        assert name in ctx


def test_build_context_truncates_long_input():
    big = dict(SAMPLE)
    big["technologies"] = [{"name": f"Tech{i}", "category": "x", "confidence": 50} for i in range(2000)]
    ctx = build_context(big)
    assert len(ctx) <= 6100          # _MAX_CONTEXT_CHARS (6000) + el sufijo
    assert "truncated" in ctx


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
