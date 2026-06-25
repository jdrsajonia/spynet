import logging
from .base_detector import BaseDetector
from config.constants import PROBE_PATH_SCORE

logger = logging.getLogger("spynet.detectors.backend")


class BackendDetector(BaseDetector):

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
        cookie_names = " ".join((cookies or {}).keys()).lower()
        js_combined  = " ".join(js_contents or []).lower()
        res_combined = " ".join(resources or []).lower()
        # probe_responses: { "/ruta/": "contenido de la respuesta" }
        probe_combined = " ".join((probe_responses or {}).values()).lower()

        logger.debug("Running backend detection against %d signatures", len(self.signatures))

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

            # ── 4. Cookies ────────────────────────────────────────────────
            s, e = self._scan_text(sig["cookie_patterns"], w["cookie_patterns"], cookie_names, "cookie '", "' presente")
            score += s; evidence += e

            # ── 5. Contenido JS descargado (estrategia 2) ─────────────────
            s, e = self._scan_text(sig.get("js_patterns", []), w.get("js_patterns", 0), js_combined, "JS contiene '", "'")
            score += s; evidence += e

            # ── 6. Recursos estáticos (estrategia 5) ──────────────────────
            s, e = self._scan_text(sig.get("resource_patterns", []), w.get("resource_patterns", 0), res_combined, "recurso '", "' encontrado")
            score += s; evidence += e

            # ── 7. Rutas sondeadas (estrategia 3) ─────────────────────────
            if probe_combined:
                probe_paths = sig.get("probe_paths", {})
                for path, indicators in probe_paths.items():
                    path_response = (probe_responses or {}).get(path, "").lower()
                    if path_response:
                        for indicator in indicators:
                            if indicator.lower() in path_response:
                                score += PROBE_PATH_SCORE
                                evidence.append(f"ruta '{path}' contiene '{indicator}'")

            if score >= sig["threshold"] and evidence:
                logger.info("Backend detected: %s (score=%d, threshold=%d)", tech, score, sig["threshold"])
                results.append(self._build_result(tech, "backend", score, evidence))

        logger.debug("Backend detection complete: %d technologies found", len(results))
        return results