import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .base_services import BaseServices
from whois import extract_domain

logger = logging.getLogger("spynet.services.wayback")


class WaybackService(BaseServices):
    def __init__(self):
        self.cdx_api = "http://web.archive.org/cdx/search/cdx"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        self._session = requests.Session()
        self._session.mount("http://", HTTPAdapter(max_retries=retry))
        self._session.mount("https://", HTTPAdapter(max_retries=retry))


    def fetch_service(self, url, _depth_data=False):
        return self.get_wayback(url)


    def get_archive_pages(self, domain: str) -> int:
        """
        Número de PÁGINAS en que la CDX API parte el índice de capturas del dominio
        (parámetro showNumPages). NO es el número de snapshots: cada página agrupa
        miles de capturas. Sirve como métrica barata de "qué tan archivado está" un
        dominio sin descargar todas las filas. Para el conteo exacto habría que
        paginar el índice completo, lo cual es lento y pesado.
        """
        response = self._session.get(self.cdx_api, params={
            "url": domain,
            "output": "json",
            "showNumPages": True
        }, headers=self.headers, timeout=15)

        try:
            data = response.json()
            return int(data[1][0])
        except (IndexError, ValueError, KeyError):
            return 0


    def get_snapshots(self, domain: str) -> list:
        response = self._session.get(self.cdx_api, params={
            "url": domain,
            "output": "json",
            "limit": 13,
            "fl": "timestamp,original",
            "collapse": "timestamp:4",
        }, headers=self.headers, timeout=15)

        data = response.json()

        if not data or len(data) <= 1:
            return []

        return [
            {
                "timestamp": timestamp,
                "url": f"https://web.archive.org/web/{timestamp}/{original}"
            }
            for timestamp, original in (row for row in data[1:] if len(row) == 2)
        ]


    def get_wayback(self, url: str) -> dict:
        try:
            domain = extract_domain(url)
            logger.info("Wayback lookup for domain: %s", domain)
            archive_pages = self.get_archive_pages(domain)
            snapshots = self.get_snapshots(domain)
            logger.info(
                "Wayback complete for %s: %d CDX pages, %d snapshots retrieved",
                domain, archive_pages, len(snapshots)
            )
            return {"archive_pages": archive_pages, "snapshots": snapshots}
        except Exception as exc:
            logger.error("Wayback lookup failed for %s: %s", url, exc)
            return None
