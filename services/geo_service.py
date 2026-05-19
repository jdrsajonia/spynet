import requests # pip install requests
from whois import extract_domain

class GeoService():
    def __init__(self):
        self.api_endpoint="http://ip-api.com/json/" # no se necesita api_key
    
    def get_geoinfo(self, url, all_data=False):
        try:
            domain=extract_domain(url)
            response=requests.get(self.api_endpoint+domain)
            data=response.json()

            if data.get("status")=="fail":
                return None

            if all_data:
                return data
            
            return {
                "country": data.get("country"),
                "city": data.get("city"),
                "isp": data.get("isp"),
                "org": data.get("org"),
                "ip": data.get("query"),
                "lat": data.get("lat"), 
                "lon": data.get("lon"),  
            }  
        
        except Exception:
            return None  #RF-14 

# service=GeoService()

# print(service.get_geoinfo("https://claude.ai/chat/0e5c59f3-bfbd-44c1-9575-d246df9608ed", True))
# print(service.get_geoinfo("google.com"))
# print(service.get_geoinfo("googasdfasdle.com"))