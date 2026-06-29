import pytest


@pytest.fixture(autouse=True)
def _reset_throttle_cache():
    """
    Limpia el historial de throttling de DRF antes de cada test. El rate limiting
    es real en runtime, pero la caché de conteos persiste entre tests del mismo
    proceso y dispararía 429 falsos al acumular requests. Cada test individual
    hace pocas llamadas, así que reiniciar por test lo neutraliza.
    """
    from django.core.cache import cache
    cache.clear()
    yield
