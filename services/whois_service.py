from datetime import datetime, timezone
import whois # pip install python-whois

class WhoisService():
    def get_whois(self, url:str, all_data=False):
        try:
            domain=whois.extract_domain(url)
            data=whois.whois(domain)

            date_creation=data.creation_date
            date_expiration=data.expiration_date

            if isinstance(date_creation, list):
                date_creation=date_creation[0]
            if isinstance(date_expiration, list):
                date_expiration=date_expiration[0]

            domain_age=None
            if date_creation:
                now=datetime.now(timezone.utc)
                date_creation = date_creation.replace(tzinfo=timezone.utc) if date_creation.tzinfo is None else date_creation
                domain_age=round(((now-date_creation).days)/365,1) #RF-06

            if all_data:
                return dict(data)
            
            return {
                "registrar": data.registrar,
                "registrant": data.registrant,
                "creation_date": str(date_creation),
                "expiration_date": str(date_expiration),
                "domain_age_years": domain_age
            }
            
        except Exception:
            return None  #RF-14

# service=WhoisService()
# print(service.get_whois("https://claude.ai/chat/0e5c59f3-bfbd-44c1-9575-d246df9608ed", True))
# print(service.get_whois("httpsd246df9608ed"))