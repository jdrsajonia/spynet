"""Tests del auditor de seguridad pasivo (función pura, sin red ni BD)."""
from core.security_auditor import audit

# Todos los security headers presentes.
ALL_HEADERS = {
    "Content-Security-Policy":   "default-src 'self'",
    "Strict-Transport-Security": "max-age=31536000",
    "X-Frame-Options":           "DENY",
    "X-Content-Type-Options":    "nosniff",
    "Referrer-Policy":           "no-referrer",
    "Permissions-Policy":        "geolocation=()",
}
GOOD_TLS = {"valid": True}
GOOD_EMAIL = {"dmarc": "v=DMARC1; p=reject", "dnssec": True}


def test_full_posture_scores_A():
    # Todo lo bueno presente → nota A, sin hallazgos.
    r = audit(ALL_HEADERS, [], [], tls=GOOD_TLS, email=GOOD_EMAIL)
    assert r["grade"] == "A"
    assert r["score"] == 100
    assert r["findings"] == []


def test_nothing_is_F():
    # Sin TLS, sin headers, sin correo → nota baja.
    r = audit({}, [], [], tls=None, email=None)
    assert r["grade"] == "F"
    assert r["score"] < 40
    # Debe listar los faltantes (HTTPS, HSTS, CSP, …).
    titles = " ".join(f["title"] for f in r["findings"]).lower()
    assert "https" in titles and "hsts" in titles


def test_valid_tls_rewards_score():
    # Mismos headers; tener TLS válido sube la nota (premia lo bueno).
    without = audit(ALL_HEADERS, [], [], tls=None, email=GOOD_EMAIL)["score"]
    with_tls = audit(ALL_HEADERS, [], [], tls=GOOD_TLS, email=GOOD_EMAIL)["score"]
    assert with_tls > without


def test_csp_report_only_counts_as_csp():
    # CSP en modo report-only NO debe marcarse como "falta CSP".
    headers = {**ALL_HEADERS}
    del headers["Content-Security-Policy"]
    headers["Content-Security-Policy-Report-Only"] = "default-src 'self'"
    r = audit(headers, [], [], tls=GOOD_TLS, email=GOOD_EMAIL)
    assert not any("content-security-policy" in f["title"].lower() for f in r["findings"])


def test_insecure_cookie_is_flagged():
    cookie = {"name": "sid", "secure": False, "httponly": False, "samesite": None}
    r = audit(ALL_HEADERS, [cookie], [], tls=GOOD_TLS, email=GOOD_EMAIL)
    cookie_findings = [f for f in r["findings"] if f["category"] == "cookies"]
    assert len(cookie_findings) == 1


def test_version_disclosure_header_flagged():
    r = audit({**ALL_HEADERS, "Server": "nginx/1.18.0"}, [], [], tls=GOOD_TLS, email=GOOD_EMAIL)
    disclosure = [f for f in r["findings"] if f["category"] == "disclosure"]
    assert disclosure and "server" in disclosure[0]["title"].lower()


def test_eol_version_flagged():
    techs = [{"name": "PHP", "version": "7.2", "category": "backend"}]
    r = audit(ALL_HEADERS, [], techs, tls=GOOD_TLS, email=GOOD_EMAIL)
    eol = [f for f in r["findings"] if f["category"] == "outdated"]
    assert eol and eol[0]["tech"] == "PHP"


def test_modern_version_not_flagged():
    techs = [{"name": "PHP", "version": "8.3", "category": "backend"}]
    r = audit(ALL_HEADERS, [], techs, tls=GOOD_TLS, email=GOOD_EMAIL)
    assert not any(f["category"] == "outdated" for f in r["findings"])
