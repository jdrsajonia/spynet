import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from core.js_fetcher import fetch_js_contents
from core.signature_loader import SignatureLoader
from detectors.detector_factory import DetectorFactory
from services.dns_service import DnsRecordService
from services.geo_service import GeoService
from services.whois_service import WhoisService
from services.wayback_service import WaybackService


class Analyzer:  # patrón Facade
    """
    Orquesta todos los servicios y detectores desde un único punto de entrada.

    Estrategias de detección aplicadas:
      1. Pattern matching sobre HTML, headers, cookies, script src  (original)
      2. Análisis de contenido de archivos JS descargados           (nuevo)
      3. Sondeo de rutas conocidas (/wp-json/, /admin/, etc.)       (nuevo)
      5. Análisis de rutas de recursos estáticos (CSS/JS/imágenes)  (nuevo)
    """

    TIMEOUT = 10
    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }

    def __init__(self):
        self._factory = DetectorFactory()
        self._dns     = DnsRecordService()
        self._geo     = GeoService()
        self._whois   = WhoisService()
        self._wayback = WaybackService()
        self._probe_paths = self._collect_probe_paths()

    # ──────────────────────────────────────────────────────────────────────
    # Análisis completo
    # ──────────────────────────────────────────────────────────────────────

    def analyze(self, url: str, depth_data: bool = False) -> dict:
        url = self._normalize_url(url)

        # 1. Servicios de infraestructura — CDNDetector reutiliza NS e IP
        dns_data   = self._dns.fetch_service(url)
        geo_data   = self._geo.fetch_service(url, depth_data)
        whois_data = self._whois.fetch_service(url, depth_data)
        wayback    = self._wayback.fetch_service(url)

        # 2. Petición HTTP principal al sitio
        page = self._fetch_page(url)

        # 3. Detección de tecnologías
        technologies = []
        if page:
            ns_list   = (dns_data or {}).get("NS", [])
            server_ip = (geo_data or {}).get("ip", "")
            technologies = self._run_detectors(page, url, ns_list, server_ip)

        return {
            "url":          url,
            "technologies": technologies,
            "dns":          dns_data,
            "whois":        whois_data,
            "geo":          geo_data,
            "wayback":      wayback,
        }

    # ──────────────────────────────────────────────────────────────────────
    # RF-19: Análisis pasivo de snapshot histórico
    # ──────────────────────────────────────────────────────────────────────

    def analyze_snapshot(self, snapshot_url: str) -> dict | None:
        """
        Análisis pasivo de un snapshot de Wayback Machine (RF-19).
        Solo corre FrontendDetector y BackendDetector sobre el HTML histórico.
        Excluye CDNDetector, DNS, WHOIS, Geo y Wayback por definición.
        No aplica sondeo de rutas ni descarga JS — el snapshot es solo HTML.
        """
        page = self._fetch_page(snapshot_url)
        if not page:
            return None

        detectors    = self._factory.create_all()
        technologies = []
        technologies += detectors["frontend"].detect(
            page["html"], page["headers"], page["scripts"]
        )
        technologies += detectors["backend"].detect(
            page["html"], page["headers"], page["scripts"], page["cookies"]
        )
        return {"snapshot_url": snapshot_url, "technologies": technologies}

    # ──────────────────────────────────────────────────────────────────────
    # Helpers privados
    # ──────────────────────────────────────────────────────────────────────

    def _run_detectors(self, page: dict, base_url: str, ns_list: list, server_ip: str) -> list[dict]:
        """
        Ejecuta las tres estrategias nuevas y pasa todo a los detectores.
        """
        html    = page["html"]
        headers = page["headers"]
        scripts = page["scripts"]
        cookies = page["cookies"]

        # Estrategia 2: descargar contenido de archivos JS
        js_contents = fetch_js_contents(base_url, scripts)

        # Estrategia 3: sondear rutas conocidas
        probe_responses = self._probe_paths_request(base_url)

        # Estrategia 5: extraer rutas de recursos estáticos
        resources = self._extract_resources(html, base_url)

        detectors = self._factory.create_all()
        results   = []

        results += detectors["frontend"].detect(
            html, headers, scripts,
            js_contents=js_contents,
            resources=resources,
        )
        results += detectors["backend"].detect(
            html, headers, scripts, cookies,
            js_contents=js_contents,
            resources=resources,
            probe_responses=probe_responses,
        )
        results += detectors["cdn"].detect(
            html, headers, scripts, ns_list, server_ip
        )

        return results

    def _probe_paths_request(self, base_url: str) -> dict:
        """
        Estrategia 3: hace GET a cada ruta conocida y guarda la respuesta.
        Retorna { "/ruta/": "contenido" } para las que respondan 200.
        """
        responses = {}
        for path in self._probe_paths:
            try:
                url = urljoin(base_url, path)
                r   = requests.get(
                    url,
                    headers=self.DEFAULT_HEADERS,
                    timeout=5,
                    allow_redirects=False   # no seguir redirects — un 301 a /login no es wp-json
                )
                if r.status_code == 200:
                    responses[path] = r.text[:5000]  # limitar tamaño
            except Exception:
                pass
        return responses

    def _extract_resources(self, html: str, base_url: str) -> list[str]:
        """
        Estrategia 5: extrae rutas de CSS, imágenes y scripts del HTML.
        """
        try:
            soup      = BeautifulSoup(html, "html.parser")
            resources = []

            for tag in soup.find_all("link", rel=lambda r: r and "stylesheet" in r):
                href = tag.get("href", "")
                if href:
                    resources.append(href)

            for tag in soup.find_all("img"):
                src = tag.get("src", "")
                if src:
                    resources.append(src)

            for tag in soup.find_all("script", src=True):
                resources.append(tag["src"])

            return resources
        except Exception:
            return []

    def _collect_probe_paths(self) -> list[str]:
        """
        Recopila todas las rutas de sondeo definidas en signatures.json
        para no hardcodearlas aquí.
        """
        loader = SignatureLoader()
        paths  = set()
        for category in loader.get_all().values():
            for sig in category.values():
                for path in sig.get("probe_paths", {}).keys():
                    paths.add(path)
        return list(paths)

    def _normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def _fetch_page(self, url: str) -> dict | None:
        try:
            response = requests.get(
                url,
                headers=self.DEFAULT_HEADERS,
                timeout=self.TIMEOUT,
                allow_redirects=True
            )
            html    = response.text
            headers = dict(response.headers)
            cookies = {c.name: c.value for c in response.cookies}
            scripts = self._extract_scripts(html)
            return {"html": html, "headers": headers, "cookies": cookies, "scripts": scripts}
        except Exception:
            return None

    def _extract_scripts(self, html: str) -> list[str]:
        try:
            soup = BeautifulSoup(html, "html.parser")
            return [tag["src"] for tag in soup.find_all("script", src=True)]
        except Exception:
            return re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)


if __name__ == "__main__":
    import json
    result = Analyzer().analyze("pivigames.blog")
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))