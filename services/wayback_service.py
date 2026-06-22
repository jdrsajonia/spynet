import logging
import requests
from .base_services import BaseServices
from whois import extract_domain

logger = logging.getLogger("spynet.services.wayback")


class WaybackService(BaseServices):
    def __init__(self):
        self.cdx_api = "http://web.archive.org/cdx/search/cdx"
        self.headers = {"User-Agent": "Mozilla/5.0"}


    def fetch_service(self, url, _depth_data=False):
        return self.get_wayback(url)


    def get_count(self, domain: str) -> int:
        response = requests.get(self.cdx_api, params={
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
        response = requests.get(self.cdx_api, params={
            "url": domain,
            "output": "json",
            "limit": 5,
            "fl": "timestamp,original",
            "collapse": "digest"
        }, headers=self.headers, timeout=15)

        data = response.json()

        if not data or len(data) <= 1:
            return []

        snapshots = []
        for row in data[1:]:
            if len(row) != 2:
                continue
            timestamp, original = row
            snapshots.append({
                "timestamp": timestamp,
                "url": f"https://web.archive.org/web/{timestamp}/{original}"
            })

        return snapshots


    def get_wayback(self, url: str) -> dict:
        try:
            domain = extract_domain(url)
            logger.info("Wayback lookup for domain: %s", domain)
            count = self.get_count(domain)
            snapshots = self.get_snapshots(domain)
            logger.info(
                "Wayback complete for %s: %d total snapshots, %d recent retrieved",
                domain, count, len(snapshots)
            )
            return {"snapshot_count": count, "snapshots": snapshots}
        except Exception as exc:
            logger.error("Wayback lookup failed for %s: %s", url, exc)
            return None
