"""
Unit tests de los servicios de dominio (sin red real).

HTTP mockeado con `responses` (Geo, Wayback); DNS y WHOIS con monkeypatch,
porque no usan requests sino dnspython y python-whois.
"""
import types
from datetime import datetime

import responses

from services.dns_service import DnsRecordService
from services.geo_service import GeoService
from services.wayback_service import WaybackService
from services.whois_service import WhoisService

CDX_API = "http://web.archive.org/cdx/search/cdx"


class TestGeoService:
    @responses.activate
    def test_parses_summary(self):
        responses.add(
            responses.GET, "http://ip-api.com/json/example.com",
            json={
                "status": "success", "country": "United States", "city": "Los Angeles",
                "isp": "Cloudflare", "org": "Cloudflare", "query": "1.2.3.4",
                "lat": 34.05, "lon": -118.24,
            },
            status=200,
        )
        result = GeoService().get_geoinfo("https://example.com")
        assert result["country"] == "United States"
        assert result["ip"] == "1.2.3.4"
        assert result["isp"] == "Cloudflare"

    @responses.activate
    def test_fail_status_returns_none(self):
        responses.add(
            responses.GET, "http://ip-api.com/json/example.com",
            json={"status": "fail", "message": "reserved range"}, status=200,
        )
        assert GeoService().get_geoinfo("https://example.com") is None


class TestWaybackService:
    @responses.activate
    def test_parses_pages_and_snapshots(self):
        # 1ª llamada: showNumPages -> número de páginas CDX.
        responses.add(responses.GET, CDX_API, json=[["numpages"], ["9"]], status=200)
        # 2ª llamada: las capturas.
        responses.add(
            responses.GET, CDX_API,
            json=[
                ["timestamp", "original"],
                ["20230101000000", "http://example.com/"],
                ["20240101000000", "http://example.com/"],
            ],
            status=200,
        )
        result = WaybackService().get_wayback("https://example.com")
        assert result["archive_pages"] == 9
        assert len(result["snapshots"]) == 2
        assert result["snapshots"][0]["timestamp"] == "20230101000000"
        assert result["snapshots"][0]["url"].startswith(
            "https://web.archive.org/web/20230101000000/"
        )

    @responses.activate
    def test_no_history_returns_empty_snapshots(self):
        responses.add(responses.GET, CDX_API, json=[["numpages"], ["0"]], status=200)
        responses.add(responses.GET, CDX_API, json=[], status=200)
        result = WaybackService().get_wayback("https://example.com")
        assert result["archive_pages"] == 0
        assert result["snapshots"] == []


class TestDnsRecordService:
    def test_parses_records_and_skips_missing(self, monkeypatch):
        available = {"A": ["1.2.3.4"], "MX": ["10 mail.example.com"]}

        def fake_resolve(domain, record_type):
            if record_type in available:
                return available[record_type]
            raise Exception("no records of this type")

        monkeypatch.setattr("dns.resolver.resolve", fake_resolve)
        records = DnsRecordService().get_dns_records("https://example.com")
        assert records["A"] == ["1.2.3.4"]
        assert records["MX"] == ["10 mail.example.com"]
        assert records["CNAME"] == []  # falló -> queda vacío, sin abortar


class TestWhoisService:
    def test_parses_and_computes_age(self, monkeypatch):
        fake = types.SimpleNamespace(
            registrar="Test Registrar", registrant=None,
            creation_date=datetime(2000, 1, 1), expiration_date=datetime(2030, 1, 1),
        )
        monkeypatch.setattr("whois.whois", lambda domain: fake)
        result = WhoisService().get_whois("https://example.com")
        assert result["registrar"] == "Test Registrar"
        assert result["domain_age_years"] > 20

    def test_handles_list_dates(self, monkeypatch):
        fake = types.SimpleNamespace(
            registrar="R", registrant=None,
            creation_date=[datetime(2010, 6, 1), datetime(2010, 6, 2)],
            expiration_date=[datetime(2030, 6, 1)],
        )
        monkeypatch.setattr("whois.whois", lambda domain: fake)
        result = WhoisService().get_whois("https://example.com")
        assert result["domain_age_years"] > 10
