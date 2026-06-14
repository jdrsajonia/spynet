from .base_detector import BaseDetector


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
        scripts_low  = [s.lower() for s in scripts]
        cookies_low  = {k.lower(): v.lower() for k, v in (cookies or {}).items()}
        js_combined  = " ".join(js_contents or []).lower()
        res_combined = " ".join(resources or []).lower()
        # probe_responses: { "/ruta/": "contenido de la respuesta" }
        probe_combined = " ".join((probe_responses or {}).values()).lower()

        for tech, sig in self.signatures.items():
            score    = 0
            evidence = []

            # ── 1. HTML ───────────────────────────────────────────────────
            w = sig["weights"]["html_patterns"]
            for p in sig["html_patterns"]:
                if p.lower() in html_lower:
                    score += w
                    evidence.append(f"HTML contiene '{p}'")

            # ── 2. Script src ─────────────────────────────────────────────
            w = sig["weights"]["script_patterns"]
            for p in sig["script_patterns"]:
                if any(p.lower() in s for s in scripts_low):
                    score += w
                    evidence.append(f"script src contiene '{p}'")

            # ── 3. Headers ────────────────────────────────────────────────
            w = sig["weights"]["header_patterns"]
            for p in sig["header_patterns"]:
                if self._match_header(p, hdrs):
                    score += w
                    evidence.append(f"header '{p}' presente")

            # ── 4. Cookies ────────────────────────────────────────────────
            w = sig["weights"]["cookie_patterns"]
            for p in sig["cookie_patterns"]:
                if any(p.lower() in name for name in cookies_low):
                    score += w
                    evidence.append(f"cookie '{p}' presente")

            # ── 5. Contenido JS descargado (estrategia 2) ─────────────────
            w = sig["weights"].get("js_patterns", 0)
            if w and js_combined:
                for p in sig.get("js_patterns", []):
                    if p.lower() in js_combined:
                        score += w
                        evidence.append(f"JS contiene '{p}'")

            # ── 6. Recursos estáticos (estrategia 5) ──────────────────────
            w = sig["weights"].get("resource_patterns", 0)
            if w and res_combined:
                for p in sig.get("resource_patterns", []):
                    if p.lower() in res_combined:
                        score += w
                        evidence.append(f"recurso '{p}' encontrado")

            # ── 7. Rutas sondeadas (estrategia 3) ─────────────────────────
            if probe_combined:
                probe_paths = sig.get("probe_paths", {})
                for path, indicators in probe_paths.items():
                    path_response = (probe_responses or {}).get(path, "").lower()
                    if path_response:
                        for indicator in indicators:
                            if indicator.lower() in path_response:
                                score += 60  # señal fuerte — ruta específica confirmada
                                evidence.append(f"ruta '{path}' contiene '{indicator}'")

            if score >= sig["threshold"] and evidence:
                results.append(self._build_result(tech, "backend", score, evidence))

        return results