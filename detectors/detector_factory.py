from .frontend_detector import FrontendDetector
from .backend_detector import BackendDetector
from .cdn_detector import CDNDetector
from .base_detector import BaseDetector
from core.signature_loader import SignatureLoader


class DetectorFactory:
    """
    Patrón Factory: crea instancias de detectores inyectándoles las firmas
    correspondientes desde el Singleton SignatureLoader.

    El Analyzer no sabe cómo se construyen los detectores ni qué firmas usan;
    simplemente pide un detector por categoría (RNF-03: escalabilidad).

    Para agregar un nuevo detector (ej. CMSDetector):
    1. Crear la clase en detectors/cms_detector.py extendiendo BaseDetector
    2. Agregar sus firmas en core/signatures.json bajo la clave "cms"
    3. Registrarlo en el dict _registry aquí abajo — sin tocar el Analyzer.
    """

    _registry = {
        "frontend": FrontendDetector,
        "backend":  BackendDetector,
        "cdn":      CDNDetector,
    }

    def __init__(self):
        self._loader = SignatureLoader()  # Singleton: misma instancia siempre

    def create(self, category: str) -> BaseDetector:
        """
        Crea y retorna un detector para la categoría solicitada.

        Args:
            category: "frontend", "backend" o "cdn"

        Returns:
            Instancia del detector con sus firmas ya inyectadas.

        Raises:
            ValueError si la categoría no existe.
        """
        detector_class = self._registry.get(category)
        if not detector_class:
            raise ValueError(f"Categoría de detector desconocida: '{category}'. "
                             f"Disponibles: {list(self._registry.keys())}")

        signatures = self._loader.get(category)
        return detector_class(signatures)

    def create_all(self) -> dict[str, BaseDetector]:
        """Crea y retorna todos los detectores disponibles de una vez."""
        return {cat: self.create(cat) for cat in self._registry}

    @classmethod
    def register(cls, category: str, detector_class: type):
        """
        Permite registrar nuevos detectores en tiempo de ejecución.
        Útil para extensiones o plugins futuros.
        """
        cls._registry[category] = detector_class