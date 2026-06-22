import logging
from datetime import datetime, timezone
from .base_services import BaseServices
import whois # pip install python-whois

logger = logging.getLogger("spynet.services.whois")


class WhoisService(BaseServices):

    def fetch_service(self, url, depth_data = False):
        return self.get_whois(url, depth_data)


    def get_whois(self, url: str, all_data=False):
        try:
            domain = whois.extract_domain(url)
            logger.info("WHOIS lookup for domain: %s", domain)
            data = whois.whois(domain)

            date_creation = data.creation_date
            date_expiration = data.expiration_date

            if isinstance(date_creation, list):
                date_creation = date_creation[0]
            if isinstance(date_expiration, list):
                date_expiration = date_expiration[0]

            domain_age = None
            if date_creation:
                now = datetime.now(timezone.utc)
                date_creation = date_creation.replace(tzinfo=timezone.utc) if date_creation.tzinfo is None else date_creation
                domain_age = round(((now - date_creation).days) / 365, 1)  #RF-06

            logger.info(
                "WHOIS complete for %s: registrar=%s, age=%.1f years",
                domain, data.registrar, domain_age or 0
            )

            if all_data:
                return dict(data)

            return {
                "registrar": data.registrar,
                "registrant": data.registrant,
                "creation_date": str(date_creation),
                "expiration_date": str(date_expiration),
                "domain_age_years": domain_age
            }

        except Exception as exc:
            logger.error("WHOIS lookup failed for %s: %s", url, exc)
            return None  #RF-14