import logging
from .base_detector import BaseDetector

logger = logging.getLogger("spynet.detectors.frontend")


class FrontendDetector(BaseDetector):

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

        results      = []
        html_lower   = html.lower()
        hdrs         = {k.lower(): v.lower() for k, v in headers.items()}
        script_text  = " ".join(scripts).lower()
        js_combined  = " ".join(js_contents or []).lower()
        res_combined = " ".join(resources or []).lower()

        logger.debug("Running frontend detection against %d signatures", len(self.signatures))

        for tech, sig in self.signatures.items():
            score    = 0
            evidence = []
            w        = sig["weights"]

            # ── 1. HTML ───────────────────────────────────────────────────
            s, e = self._scan_text(sig["html_patterns"], w["html_patterns"], html_lower, "HTML contiene '", "'")
            score += s; evidence += e

            # ── 2. Script src ─────────────────────────────────────────────
            s, e = self._scan_text(sig["script_patterns"], w["script_patterns"], script_text, "script src contiene '", "'")
            score += s; evidence += e

            # ── 3. Headers ────────────────────────────────────────────────
            s, e = self._scan_headers(sig["header_patterns"], w["header_patterns"], hdrs)
            score += s; evidence += e

            # ── 4. Contenido JS descargado (estrategia 2) ─────────────────
            s, e = self._scan_text(sig.get("js_patterns", []), w.get("js_patterns", 0), js_combined, "JS contiene '", "'")
            score += s; evidence += e

            # ── 5. Recursos estáticos (estrategia 5) ──────────────────────
            s, e = self._scan_text(sig.get("resource_patterns", []), w.get("resource_patterns", 0), res_combined, "recurso '", "' encontrado")
            score += s; evidence += e

            if score >= sig["threshold"] and evidence:
                version = self._extract_version(sig, [script_text, res_combined, js_combined, html_lower])
                logger.info("Frontend detected: %s (score=%d, threshold=%d, version=%s)", tech, score, sig["threshold"], version)
                results.append(self._build_result(tech, "frontend", score, evidence, version))

        logger.debug("Frontend detection complete: %d technologies found", len(results))
        return results