import logging
from .base_detector import BaseDetector
from config.constants import MAX_CATEGORY_MATCHES

logger = logging.getLogger("spynet.detectors.cdn")


class CDNDetector(BaseDetector):
    """
    Detecta CDN y proveedores de hosting: Cloudflare, AWS, Vercel, Netlify, GitHub Pages.

    Recibe además los nameservers DNS y la IP del servidor (provenientes del DNSService
    y GeoService), que son la señal más fuerte para identificar infraestructura (RF-04, US-02).
    """

    def detect(
        self,
        html: str,
        headers: dict,
        scripts: list[str],
        nameservers: list[str] = None,
        server_ip: str = None
    ) -> list[dict]:

        results = []
        headers_lower = {k.lower(): v.lower() for k, v in headers.items()}
        ns_lower = [ns.lower() for ns in (nameservers or [])]
        ip = server_ip or ""

        logger.debug(
            "Running CDN detection against %d signatures (ip=%s, ns=%d)",
            len(self.signatures), ip or "unknown", len(ns_lower)
        )

        for tech_name, sig in self.signatures.items():
            score = 0
            evidence = []

            # ── Señales en headers HTTP ───────────────────────────────────
            s, e = self._scan_headers(sig["header_patterns"], sig["weights"]["header_patterns"], headers_lower)
            score += s; evidence += e

            # ── Señales en nameservers DNS ────────────────────────────────
            w_ns = sig["weights"]["ns_patterns"]
            ns_matches = 0
            for pattern in sig["ns_patterns"]:
                if any(pattern.lower() in ns for ns in ns_lower):
                    if ns_matches < MAX_CATEGORY_MATCHES:
                        score += w_ns
                        ns_matches += 1
                    evidence.append(f"nameserver contiene '{pattern}'")

            # ── Señales en rango de IP ────────────────────────────────────
            w_ip = sig["weights"]["ip_ranges"]
            ip_matches = 0
            for ip_prefix in sig["ip_ranges"]:
                if ip.startswith(ip_prefix):
                    if ip_matches < MAX_CATEGORY_MATCHES:
                        score += w_ip
                        ip_matches += 1
                    evidence.append(f"IP {ip} pertenece al rango de {tech_name}")

            if score >= sig["threshold"] and evidence:
                logger.info("CDN detected: %s (score=%d, threshold=%d)", tech_name, score, sig["threshold"])
                results.append(self._build_result(tech_name, "cdn", score, evidence))

        logger.debug("CDN detection complete: %d providers found", len(results))
        return results