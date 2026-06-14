import json
import os


class SignatureLoader:
    """
    Patrón Singleton: carga signatures.json una sola vez en memoria.
    Todos los detectores comparten la misma instancia sin releer el archivo.
    """

    _instance = None
    _signatures: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "signatures.json")
        with open(path, "r", encoding="utf-8") as f:
            self._signatures = json.load(f)

    def get(self, category: str) -> dict:
        """Retorna las firmas de una categoría: 'frontend', 'backend' o 'cdn'."""
        return self._signatures.get(category, {})

    def get_all(self) -> dict:
        return self._signatures