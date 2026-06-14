from abc import ABC, abstractmethod


class BaseDetector(ABC):
    """
    Clase base abstracta para todos los detectores de tecnología.
    Define la interfaz común que deben implementar FrontendDetector,
    BackendDetector y CDNDetector (patrón Strategy).
    """

    def __init__(self, signatures: dict):
        self.signatures = signatures

    @abstractmethod
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
        """
        Analiza todas las fuentes disponibles y retorna las tecnologías detectadas.

        Args:
            html:            HTML crudo de la página
            headers:         headers HTTP de la respuesta
            scripts:         lista de src de <script> encontrados en el HTML
            cookies:         cookies de la respuesta
            js_contents:     contenido descargado de archivos JS (estrategia 2)
            resources:       rutas de CSS/JS/imágenes del HTML (estrategia 5)
            probe_responses: respuestas de rutas sondeadas, ej:
                             { "/wp-json/": "{ namespaces: ... }" } (estrategia 3)

        Returns:
            [{ "name", "category", "confidence", "evidence" }, ...]
        """
        pass

    def _match_header(self, pattern: str, headers_lower: dict) -> bool:
        """
        Evalúa un patrón de header. Soporta:
          - "cf-ray"               → solo verifica que la clave exista
          - "server: cloudflare"   → verifica clave y valor
        Evita el bug de '' in '' que causaba falsos positivos.
        """
        key, _, value = pattern.partition(": ")
        header_val = headers_lower.get(key.lower(), "")
        return (
            (bool(value) and value.lower() in header_val) or
            (not value and key.lower() in headers_lower)
        )

    def _score_to_confidence(self, score: int) -> int:
        return min(score, 100)

    def _build_result(self, name: str, category: str, score: int, evidence: list[str]) -> dict:
        return {
            "name":       name,
            "category":   category,
            "confidence": self._score_to_confidence(score),
            "evidence":   "; ".join(evidence)
        }