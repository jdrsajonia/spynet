"""
Inspección del certificado TLS/SSL de un sitio (pasivo: solo hace el handshake,
no envía datos). Distinto del WHOIS: aquí vemos quién EMITIÓ el certificado, su
validez propia (≠ expiración del dominio), los dominios que cubre y la versión
de TLS negociada.

Usa solo la stdlib (ssl/socket) — sin dependencias. Para certificados válidos
(la gran mayoría) devuelve el detalle completo; para inválidos/autofirmados
reporta el motivo sin abortar el análisis (RF-14).
"""
import logging
import socket
import ssl
from datetime import datetime, timezone
from urllib.parse import urlparse

from .base_services import BaseServices

logger = logging.getLogger("spynet.services.tls")


class TlsService(BaseServices):

    def fetch_service(self, url: str, _depth_data: bool = False) -> dict | None:
        return self.get_certificate(url)

    def get_certificate(self, url: str, port: int = 443, timeout: int = 6) -> dict | None:
        """
        Devuelve info del certificado TLS del host de `url`, o None si no hay
        HTTPS / el host no responde. { valid: false, error } si el cert no valida.
        """
        host = _host_from_url(url)
        if not host:
            return None

        context = ssl.create_default_context()
        try:
            with socket.create_connection((host, port), timeout=timeout) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    version = ssock.version()
                    logger.info("TLS cert read for %s (%s)", host, version)
                    return _parse_cert(cert, version)
        except ssl.SSLCertVerificationError as exc:
            logger.info("TLS cert verification failed for %s: %s", host, exc)
            return {"valid": False, "error": getattr(exc, "verify_message", None) or str(exc)}
        except Exception as exc:
            logger.info("TLS lookup failed for %s: %s", host, exc)
            return None


def _parse_cert(cert: dict, version: str) -> dict:
    subject = _name(cert.get("subject"))
    issuer = _name(cert.get("issuer"))
    valid_from = _parse_cert_dt(cert.get("notBefore"))
    valid_to = _parse_cert_dt(cert.get("notAfter"))
    days = (valid_to - datetime.now(timezone.utc)).days if valid_to else None
    sans = [v for (t, v) in cert.get("subjectAltName", ()) if t == "DNS"]
    return {
        "valid":          True,
        "issuer":         issuer.get("organizationName") or issuer.get("commonName"),
        "subject_cn":     subject.get("commonName"),
        "valid_from":     valid_from.isoformat() if valid_from else None,
        "valid_to":       valid_to.isoformat() if valid_to else None,
        "days_to_expiry": days,
        "tls_version":    version,
        "san":            sans,
    }


def _name(rdn_sequence) -> dict:
    """Aplana la estructura de nombre de OpenSSL: ((('commonName','x'),),…) → {…}."""
    out = {}
    for rdn in rdn_sequence or ():
        for key, value in rdn:
            out[key] = value
    return out


def _parse_cert_dt(value: str):
    # Formato de OpenSSL: 'Jun  1 12:00:00 2025 GMT'
    if not value:
        return None
    try:
        return datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _host_from_url(url: str) -> str | None:
    parsed = urlparse(url if "://" in url else "https://" + url)
    return parsed.hostname
