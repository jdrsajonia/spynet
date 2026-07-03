import logging
from .base_detector import BaseDetector

logger = logging.getLogger("spynet.detectors.server")


class ServerDetector(BaseDetector):
    """
    Detecta el servidor web / runtime de infraestructura: Nginx, Apache, IIS,
    LiteSpeed, etc.

    A diferencia del CDNDetector (que usa DNS e IP), la señal de un web server
    vive casi por completo en el header `Server:` de la respuesta HTTP y, en
    menor medida, en páginas de error por defecto presentes en el HTML.
    Por eso solo evalúa header_patterns y html_patterns (patrón Strategy).
    """

    def detect(
        self,
        html:             str,
        headers:          dict,
        scripts:          list[str],
        cookies:          dict       = None,
        js_contents:      list[str]  = None,
        resources:        list[str]  = None,
        probe_responses:  dict       = None,
    ) -> list[dict]:

        results    = []
        html_lower = html.lower()
        hdrs       = {k.lower(): v.lower() for k, v in headers.items()}

        logger.debug("Running server detection against %d signatures", len(self.signatures))

        for tech, sig in self.signatures.items():
            score    = 0
            evidence = []
            w        = sig["weights"]

            # ── Header Server / X-Powered-By ──────────────────────────────
            s, e = self._scan_headers(sig["header_patterns"], w["header_patterns"], hdrs)
            score += s; evidence += e

            # ── Páginas de error / firmas en el HTML ──────────────────────
            s, e = self._scan_text(
                sig.get("html_patterns", []), w.get("html_patterns", 0),
                html_lower, "HTML contiene '", "'"
            )
            score += s; evidence += e

            if score >= sig["threshold"] and evidence:
                header_text = " ".join(f"{k}: {v}" for k, v in hdrs.items())
                version = self._extract_version(sig, [header_text, html_lower])
                logger.info("Server detected: %s (score=%d, threshold=%d, version=%s)", tech, score, sig["threshold"], version)
                results.append(self._build_result(tech, "server", score, evidence, version))

        logger.debug("Server detection complete: %d servers found", len(results))
        return results
