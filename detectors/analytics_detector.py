import logging
from .base_detector import BaseDetector

logger = logging.getLogger("spynet.detectors.analytics")


class AnalyticsDetector(BaseDetector):
    """
    Detecta servicios de analítica, tag managers y píxeles de marketing
    (Google Analytics, GTM, Facebook Pixel, Hotjar, Segment, etc.).

    Son de las tecnologías más detectables: casi siempre se cargan vía un
    <script> de un dominio conocido (googletagmanager.com, connect.facebook.net)
    o dejan cookies características (_ga, _fbp). Escanea HTML, script src, JS,
    recursos y cookies (patrón Strategy).
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

        results      = []
        html_lower   = html.lower()
        script_text  = " ".join(scripts).lower()
        cookie_names = " ".join((cookies or {}).keys()).lower()
        js_combined  = " ".join(js_contents or []).lower()
        res_combined = " ".join(resources or []).lower()

        logger.debug("Running analytics detection against %d signatures", len(self.signatures))

        for tech, sig in self.signatures.items():
            score    = 0
            evidence = []
            w        = sig["weights"]

            s, e = self._scan_text(sig["html_patterns"], w["html_patterns"], html_lower, "HTML contiene '", "'")
            score += s; evidence += e

            s, e = self._scan_text(sig["script_patterns"], w["script_patterns"], script_text, "script src contiene '", "'")
            score += s; evidence += e

            s, e = self._scan_text(sig["cookie_patterns"], w["cookie_patterns"], cookie_names, "cookie '", "' presente")
            score += s; evidence += e

            s, e = self._scan_text(sig.get("js_patterns", []), w.get("js_patterns", 0), js_combined, "JS contiene '", "'")
            score += s; evidence += e

            s, e = self._scan_text(sig.get("resource_patterns", []), w.get("resource_patterns", 0), res_combined, "recurso '", "' encontrado")
            score += s; evidence += e

            if score >= sig["threshold"] and evidence:
                logger.info("Analytics detected: %s (score=%d, threshold=%d)", tech, score, sig["threshold"])
                results.append(self._build_result(tech, "analytics", score, evidence))

        logger.debug("Analytics detection complete: %d found", len(results))
        return results
