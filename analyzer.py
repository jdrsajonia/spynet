import re
import sys
import os
import logging
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from core.js_fetcher import fetch_js_contents
from core.signature_loader import SignatureLoader
from config.constants import DEFAULT_HEADERS, REQUEST_TIMEOUT, PROBE_TIMEOUT
from detectors.detector_factory import DetectorFactory
from services.dns_service import DnsRecordService
from services.geo_service import GeoService
from services.whois_service import WhoisService
from services.wayback_service import WaybackService

logger = logging.getLogger("spynet.analyzer")


class Analyzer:  # patrón Facade
    """
    Orquesta todos los servicios y detectores desde un único punto de entrada.

    Estrategias de detección aplicadas:
      1. Pattern matching sobre HTML, headers, cookies, script src
      2. Análisis de contenido de archivos JS descargados
      3. Sondeo de rutas conocidas (/wp-json/, /admin/, etc.)
      4. Señales de DNS/IP reutilizadas por CDNDetector
      5. Análisis de rutas de recursos estáticos (CSS/JS/imágenes)
    """

    def __init__(self):
        self._factory = DetectorFactory()
        self._dns     = DnsRecordService()
        self._geo     = GeoService()
        self._whois   = WhoisService()
        self._wayback = WaybackService()
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)
        self._probe_paths = self._collect_probe_paths()
        logger.debug("Analyzer initialized with %d probe paths", len(self._probe_paths))

    # ──────────────────────────────────────────────────────────────────────
    # Análisis completo
    # ──────────────────────────────────────────────────────────────────────

    def analyze(self, url: str, depth_data: bool = False, include_wayback: bool = True) -> dict:
        url = self._normalize_url(url)
        logger.info("Starting analysis for %s", url)

        # 1. Servicios de infraestructura (concurrentes) — CDNDetector reutiliza NS e IP.
        # Wayback es opcional: Compare lo excluye porque no usa el histórico y agrega
        # bastante latencia (comparar no necesita snapshots).
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_dns    = executor.submit(self._dns.fetch_service, url)
            future_geo    = executor.submit(self._geo.fetch_service, url, depth_data)
            future_whois  = executor.submit(self._whois.fetch_service, url, depth_data)
            future_wayback = executor.submit(self._wayback.fetch_service, url) if include_wayback else None

        dns_data   = future_dns.result()
        geo_data   = future_geo.result()
        whois_data = future_whois.result()
        wayback    = future_wayback.result() if future_wayback else None

        # 2. Petición HTTP principal al sitio
        page = self._fetch_page(url)

        # 3. Detección de tecnologías
        technologies = []
        if page:
            ns_list   = (dns_data or {}).get("NS", [])
            server_ip = (geo_data or {}).get("ip", "")
            technologies = self._run_detectors(page, url, ns_list, server_ip)
        else:
            logger.warning("No page content retrieved for %s — skipping technology detection", url)

        logger.info(
            "Analysis complete for %s: %d technologies detected",
            url, len(technologies)
        )
        result = {
            "url":          url,
            "technologies": technologies,
            "dns":          dns_data,
            "whois":        whois_data,
            "geo":          geo_data,
        }
        # La clave 'wayback' solo aparece si se ejecutó. Ausente = excluida a
        # propósito (no es un fallo); None = se intentó pero falló.
        if include_wayback:
            result["wayback"] = wayback
        return result

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
        logger.info("Analyzing Wayback snapshot: %s", snapshot_url)
        page = self._fetch_page(snapshot_url)
        if not page:
            logger.warning("Could not fetch snapshot: %s", snapshot_url)
            return None

        detectors    = self._factory.create_all()
        technologies = []
        technologies += detectors["frontend"].detect(
            html=page["html"], headers=page["headers"], scripts=page["scripts"]
        )
        technologies += detectors["backend"].detect(
            html=page["html"], headers=page["headers"],
            scripts=page["scripts"], cookies=page["cookies"]
        )
        logger.info(
            "Snapshot analysis complete for %s: %d technologies detected",
            snapshot_url, len(technologies)
        )
        return {"snapshot_url": snapshot_url, "technologies": technologies}

    # ──────────────────────────────────────────────────────────────────────
    # Vista Historical: evolución del stack a lo largo de las capturas de Wayback
    # ──────────────────────────────────────────────────────────────────────

    def analyze_history(self, url: str) -> dict:
        """
        Toma las ~12 capturas de Wayback del dominio (las mismas que encuentra un
        análisis normal) y corre el análisis pasivo de tecnologías sobre CADA una,
        para ver cómo evolucionó el stack en el tiempo (vista Historical).

        Pesado: una descarga por captura; se hacen en paralelo. Si no hay
        historial, devuelve la lista de snapshots vacía sin error.
        """
        url = self._normalize_url(url)
        logger.info("Starting historical analysis for %s", url)

        wayback   = self._wayback.fetch_service(url) or {}
        snapshots = wayback.get("snapshots", [])
        if not snapshots:
            logger.info("No Wayback snapshots for %s", url)
            return {"url": url, "archive_pages": wayback.get("archive_pages"), "snapshots": []}

        def _analyse_one(snap: dict) -> dict:
            result = self.analyze_snapshot(snap["url"])
            return {
                "timestamp":    snap["timestamp"],
                "url":          snap["url"],
                "technologies": (result or {}).get("technologies", []),
            }

        with ThreadPoolExecutor(max_workers=4) as executor:
            analysed = list(executor.map(_analyse_one, snapshots))

        logger.info("Historical analysis complete for %s: %d snapshots analysed", url, len(analysed))
        return {
            "url":           url,
            "archive_pages": wayback.get("archive_pages"),
            "snapshots":     analysed,
        }

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
        logger.debug("Strategy 2: downloading JS files (%d script srcs)", len(scripts))
        js_contents = fetch_js_contents(base_url, scripts, session=self._session)
        logger.debug("Strategy 2: downloaded %d JS files", len(js_contents))

        # Estrategia 3: sondear rutas conocidas
        logger.debug("Strategy 3: probing %d known paths", len(self._probe_paths))
        probe_responses = self._probe_paths_request(base_url)
        logger.debug("Strategy 3: %d probe paths responded with 200", len(probe_responses))

        # Estrategia 5: extraer rutas de recursos estáticos (reutiliza el soup ya parseado)
        resources = self._extract_resources(page.get("soup"), base_url)
        logger.debug("Strategy 5: extracted %d static resources", len(resources))

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
        # ServerDetector: solo en vivo. En snapshots el header Server lo pone
        # web.archive.org, no el sitio original, así que ahí no aplica.
        results += detectors["server"].detect(html, headers, scripts)

        return self._deduplicate(results)



    def _deduplicate(self, technologies: list[dict]) -> list[dict]:
        """Merge entries with the same name, keeping the highest confidence and all evidence."""
        seen: dict[str, dict] = {}
        for tech in technologies:
            name = tech["name"]
            if name not in seen:
                seen[name] = dict(tech)
            else:
                existing = seen[name]
                if tech["confidence"] > existing["confidence"]:
                    existing["confidence"] = tech["confidence"]
                if tech["evidence"] not in existing["evidence"]:
                    existing["evidence"] += "; " + tech["evidence"]
        return list(seen.values())



    def _probe_paths_request(self, base_url: str) -> dict:
        """
        Estrategia 3: hace GET a cada ruta conocida y guarda la respuesta.
        Retorna { "/ruta/": "contenido" } para las que respondan 200.
        """
        responses = {}
        for path in self._probe_paths:
            try:
                url = urljoin(base_url, path)
                r   = self._session.get(
                    url,
                    timeout=PROBE_TIMEOUT,
                    allow_redirects=False   # no seguir redirects — un 301 a /login no es wp-json
                )
                if r.status_code == 200:
                    responses[path] = r.text[:5000]  # limitar tamaño
                    logger.debug("Probe hit: %s returned 200", path)
            except Exception as exc:
                logger.debug("Probe failed for %s: %s", path, exc)
        return responses



    def _extract_resources(self, soup: BeautifulSoup | None, base_url: str) -> list[str]:
        """
        Estrategia 5: extrae rutas de CSS, imágenes y scripts del soup ya parseado.
        """
        if soup is None:
            return []
        try:
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
        except Exception as exc:
            logger.warning("Resource extraction failed for %s: %s", base_url, exc)
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
        if url.startswith("//"):
            url = "https:" + url
        elif not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url



    def _fetch_page(self, url: str) -> dict | None:
        logger.debug("Fetching page: %s", url)
        try:
            response = self._session.get(
                url,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            html    = response.text
            headers = dict(response.headers)
            cookies = {c.name: c.value for c in response.cookies}
            soup    = self._make_soup(html)
            scripts = self._extract_scripts(soup, html)
            logger.debug(
                "Page fetched: status=%d, html_len=%d, scripts=%d, cookies=%d",
                response.status_code, len(html), len(scripts), len(cookies)
            )
            return {"html": html, "headers": headers, "cookies": cookies, "scripts": scripts, "soup": soup}
        except Exception as exc:
            logger.error("Failed to fetch page %s: %s", url, exc)
            return None



    def _make_soup(self, html: str) -> BeautifulSoup | None:
        try:
            return BeautifulSoup(html, "html.parser")
        except Exception as exc:
            logger.warning("BeautifulSoup parsing failed: %s", exc)
            return None



    def _extract_scripts(self, soup: BeautifulSoup | None, html: str) -> list[str]:
        if soup is not None:
            try:
                return [tag["src"] for tag in soup.find_all("script", src=True)]
            except Exception as exc:
                logger.warning("BeautifulSoup script extraction failed, falling back to regex: %s", exc)
        return re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)