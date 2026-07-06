import logging
from datetime import datetime, timezone
from .base_services import BaseServices
import whois # pip install python-whois

logger = logging.getLogger("spynet.services.whois")


def _first(value):
    """WHOIS a veces devuelve listas (varias fechas/valores); toma el primero."""
    return value[0] if isinstance(value, list) and value else value


class WhoisService(BaseServices):

    def fetch_service(self, url, depth_data = False):
        return self.get_whois(url, depth_data)


    def get_whois(self, url: str, all_data=False):
        try:
            domain = whois.extract_domain(url)
            logger.info("WHOIS lookup for domain: %s", domain)
            data = whois.whois(domain)

            date_creation   = _first(data.creation_date)
            date_expiration = _first(data.expiration_date)
            date_updated    = _first(getattr(data, "updated_date", None))

            domain_age = None
            if date_creation:
                now = datetime.now(timezone.utc)
                date_creation = date_creation.replace(tzinfo=timezone.utc) if date_creation.tzinfo is None else date_creation
                domain_age = round(((now - date_creation).days) / 365, 1)  #RF-06

            # Estado (códigos EPP: clientTransferProhibited…) y emails: normalizar a lista.
            status = getattr(data, "status", None)
            emails = getattr(data, "emails", None)
            if isinstance(status, str): status = [status]
            if isinstance(emails, str): emails = [emails]

            logger.info(
                "WHOIS complete for %s: registrar=%s, age=%.1f years",
                domain, data.registrar, domain_age or 0
            )

            if all_data:
                return dict(data)

            return {
                "registrar":        data.registrar,
                "registrant":       data.registrant or getattr(data, "name", None),
                "org":              getattr(data, "org", None),
                "country":          getattr(data, "country", None),
                "emails":           emails,
                "dnssec":           getattr(data, "dnssec", None),
                "status":           status,
                "creation_date":    str(date_creation) if date_creation else None,
                "updated_date":     str(date_updated) if date_updated else None,
                "expiration_date":  str(date_expiration) if date_expiration else None,
                "domain_age_years": domain_age,
            }

        except Exception as exc:
            logger.error("WHOIS lookup failed for %s: %s", url, exc)
            return None  #RF-14