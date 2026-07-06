import logging
import dns.resolver #pip install dnspython
from .base_services import BaseServices
from whois import extract_domain

logger = logging.getLogger("spynet.services.dns")


class DnsRecordService(BaseServices):

    def fetch_service(self, url: str, _depth_data: bool = False) -> dict | None:
        return self.get_dns_records(url)


    def get_dns_records(self, url: str) -> dict:
        try:
            domain = extract_domain(url)
            logger.info("DNS lookup for domain: %s", domain)
            records = {
                "A":[],
                "AAAA":[],
                "CNAME":[],
                "NS":[],
                "MX":[],
                "TXT": []
            }

            for type_record in records.keys():
                try:
                    answers = dns.resolver.resolve(domain, type_record)
                    records[type_record] = [str(r) for r in answers]
                    logger.debug("DNS %s records for %s: %s", type_record, domain, records[type_record])
                except Exception as exc:
                    # Es normal que falte un tipo (ej. sin CNAME o sin MX); no es un error.
                    logger.debug("No %s records for %s: %s", type_record, domain, exc)

            logger.info(
                "DNS lookup complete for %s: A=%d NS=%d MX=%d",
                domain,
                len(records["A"]),
                len(records["NS"]),
                len(records["MX"]),
            )
            return records
        except Exception as exc:
            logger.error("DNS lookup failed for %s: %s", url, exc)
            return None