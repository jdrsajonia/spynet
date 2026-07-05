import logging
import dns.resolver #pip install dnspython
import dns.reversename
from .base_services import BaseServices
from whois import extract_domain

logger = logging.getLogger("spynet.services.dns")

# Resolvers públicos confiables (Google, Cloudflare). El resolver de la red local
# (ISP/universidad) suele colgarse con consultas TXT —respuestas grandes que
# requieren EDNS/TCP— y a veces devuelve vacío intermitente para A/AAAA. Usar
# 8.8.8.8/1.1.1.1 hace el DNS robusto y consistente sin importar la red.
_PUBLIC_NAMESERVERS = ["8.8.8.8", "1.1.1.1"]


class DnsRecordService(BaseServices):

    def __init__(self):
        self._resolver = dns.resolver.Resolver(configure=False)
        self._resolver.nameservers = _PUBLIC_NAMESERVERS
        self._resolver.timeout = 3
        self._resolver.lifetime = 6

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
                "TXT":[]
            }

            for type_record in records.keys():
                try:
                    answers = self._resolver.resolve(domain, type_record)
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


    def reverse_dns(self, ip: str) -> str | None:
        """
        PTR (reverse DNS) de una IP: el hostname al que "apunta de vuelta". Suele
        revelar el proveedor de hosting. Una sola consulta, sin API externa.
        """
        if not ip:
            return None
        try:
            rev = dns.reversename.from_address(ip)
            answer = self._resolver.resolve(rev, "PTR")
            return str(answer[0]).rstrip(".")
        except Exception as exc:
            logger.debug("PTR lookup failed for %s: %s", ip, exc)
            return None


    def email_security(self, url: str, _depth_data: bool = False) -> dict:
        """
        Postura de seguridad de correo/DNS del dominio (pasivo, solo DNS):
          - SPF:    registro TXT del apex con 'v=spf1' (anti-suplantación de correo)
          - DMARC:  registro TXT en _dmarc.<dominio> con 'v=DMARC1' (+ política p=)
          - DNSSEC: existencia de registros DNSKEY (firmas de la zona)
        Autocontenido para poder correr en paralelo con los demás servicios.
        """
        domain = extract_domain(url)
        return {
            "spf":    self._first_txt(domain, "v=spf1"),
            "dmarc":  self._first_txt(f"_dmarc.{domain}", "v=dmarc1"),
            "dnssec": self._has_dnssec(domain),
        }


    def _first_txt(self, name: str, contains: str) -> str | None:
        """Primer registro TXT de `name` que contenga `contains` (case-insensitive)."""
        try:
            for record in self._resolver.resolve(name, "TXT"):
                text = str(record).strip('"')
                if contains in text.lower():
                    return text
        except Exception as exc:
            logger.debug("TXT lookup failed for %s: %s", name, exc)
        return None


    def _has_dnssec(self, domain: str) -> bool:
        try:
            return len(self._resolver.resolve(domain, "DNSKEY")) > 0
        except Exception:
            return False