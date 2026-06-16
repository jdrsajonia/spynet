import logging
import requests # pip install requests
from .base_services import BaseServices
from whois import extract_domain

logger = logging.getLogger("spynet.services.geo")


class GeoService(BaseServices):
    def __init__(self):
        self.api_endpoint = "http://ip-api.com/json/"  # no se necesita api_key


    def fetch_service(self, url, depth_data = False):
        return self.get_geoinfo(url, depth_data)


    def get_geoinfo(self, url, all_data=False):
        try:
            domain = extract_domain(url)
            logger.info("Geo lookup for domain: %s", domain)
            response = requests.get(self.api_endpoint + domain, timeout=10)
            data = response.json()

            if data.get("status") == "fail":
                logger.warning("Geo API returned failure status for %s", domain)
                return None

            result = data if all_data else {
                "country": data.get("country"),
                "city": data.get("city"),
                "isp": data.get("isp"),
                "org": data.get("org"),
                "ip": data.get("query"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
            }
            logger.info(
                "Geo lookup complete for %s: ip=%s, country=%s, isp=%s",
                domain, data.get("query"), data.get("country"), data.get("isp")
            )
            return result

        except Exception as exc:
            logger.error("Geo lookup failed for %s: %s", url, exc)
            return None  #RF-14

# service=GeoService()

# print(service.get_geoinfo("https://claude.ai/chat/0e5c59f3-bfbd-44c1-9575-d246df9608ed", True))
# print(service.get_geoinfo("google.com"))
# print(service.get_geoinfo("googasdfasdle.com"))