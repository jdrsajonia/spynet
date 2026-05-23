import dns.resolver #pip install dnspython
from whois import extract_domain

class DnsRecordService():
    def get_dns_records(self, url: str) -> dict:
        try:
            domain=extract_domain(url)
            records={
                "A":[],
                "AAAA":[],
                "CNAME":[],
                "NS":[],
                "MX":[]
            }
            
            keys=records.keys()
            for type_record in keys:
                try:
                    answers=dns.resolver.resolve(domain, type_record)
                    records[type_record] = [str(r) for r in answers]
                except Exception:
                    pass
            return records
        except Exception:
            return None


# service=DnsRecordService()
# print(service.get_dns_records("https://claude.ai"))