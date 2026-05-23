import requests
from whois import extract_domain




class WaybackService():
    def __init__(self):
        self.cdx_api = "http://web.archive.org/cdx/search/cdx"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        pass


    def get_count(self, domain: str) -> int:
        response = requests.get(self.cdx_api, params={
            "url": domain,
            "output": "json",
            "showNumPages": True
        }, headers=self.headers, timeout=15)
        
        data = response.json()
        return int(data[1][0])  


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
            timestamp, original = row
            snapshots.append({
                "timestamp": timestamp,
                "url": f"https://web.archive.org/web/{timestamp}/{original}"
            })
        
        return snapshots


    def get_wayback(self, url: str) -> dict:
        try:
            domain = extract_domain(url)
            return {
                "snapshot_count": self.get_count(domain),
                "snapshots": self.get_snapshots(domain)
            }
        except Exception as e:
            # print(f"Error: {e}")  
            return None

# service=WaybackService()
# print(service.get_wayback("https://claude.ai"))