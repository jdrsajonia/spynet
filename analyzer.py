from services.dns_service import DnsRecordService
from services.geo_service import GeoService
from services.whois_service import WhoisService
from services.wayback_service import WaybackService

class Analyzer(): # patron de diseño Facade

    def __init__(self):
        self.whois=WhoisService()
        self.dns=DnsRecordService()
        self.geo=GeoService()
        self.wayback=WaybackService()
    
    def analyze(self, url, depth_data=False):
        return{
            "whois": self.whois.get_whois(url, depth_data),
            "geo": self.geo.get_geoinfo(url, depth_data),
            "dns": self.dns.get_dns_records(url),
            "wayback": self.wayback.get_wayback(url) # es el mas demorado, puede ser un cuello de botella. A veces devuelve None, a veces funciona
        }


print(Analyzer().analyze("google.com"))