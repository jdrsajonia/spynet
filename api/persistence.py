"""
Traducción entre la salida plana del Analyzer y el modelo relacional normalizado.

El Analyzer devuelve un dict con bloques anidados (technologies, dns, whois, geo,
wayback). Aquí lo descomponemos en las tablas del ERD dentro de una transacción:
si algo falla, no queda un análisis a medio escribir. Los servicios que devuelven
None se registran como AnalysisError (observabilidad, RF-14).
"""
import re
from datetime import datetime, timezone

from django.db import transaction
from whois import extract_domain

from api.models import (
    Analysis, AnalysisError, Domain, DnsRecord, DnsResult,
    GeoRecord, Technology, WaybackResult, WaybackSnapshot, WhoisRecord,
)

_SERVICE_FIELDS = ("whois", "geo", "dns", "wayback")


@transaction.atomic
def persist_analysis(result: dict, *, triggered_by: str = "api", duration_ms: int | None = None) -> Analysis:
    """Persiste un análisis en vivo completo (Domain → Analysis → records)."""
    domain, _ = Domain.objects.get_or_create(name=extract_domain(result["url"]))
    # Solo se consideran los servicios que SE INTENTARON (la clave está presente).
    # Compare excluye 'wayback' a propósito → no debe contar como fallo.
    attempted = [f for f in _SERVICE_FIELDS if f in result]
    status = "partial" if any(result.get(f) is None for f in attempted) else "completed"

    analysis = Analysis.objects.create(
        domain=domain, source_url=result["url"],
        status=status, triggered_by=triggered_by, duration_ms=duration_ms,
    )

    # Tecnologías en vivo → cuelgan del Analysis.
    _save_technologies(result.get("technologies", []), analysis=analysis)

    _save_whois(analysis, result.get("whois"))
    _save_geo(analysis, result.get("geo"))
    _save_dns(analysis, result.get("dns"))
    if "wayback" in result:
        _save_wayback(analysis, result["wayback"])

    return analysis


@transaction.atomic
def persist_snapshot(result: dict, *, duration_ms: int | None = None) -> Analysis:
    """
    Persiste el análisis pasivo de un snapshot (RF-19 / BP-03) como un registro
    independiente. Las tecnologías cuelgan de un WaybackSnapshot, tal como pide
    el ERD (Technology.snapshot).
    """
    snapshot_url = result["snapshot_url"]
    original_url = _original_url_from_snapshot(snapshot_url)
    domain, _ = Domain.objects.get_or_create(name=extract_domain(original_url))

    analysis = Analysis.objects.create(
        domain=domain, source_url=snapshot_url,
        status="completed", triggered_by="snapshot", duration_ms=duration_ms,
    )

    wayback = WaybackResult.objects.create(analysis=analysis, snapshot_count=1)
    snapshot = WaybackSnapshot.objects.create(
        wayback_result=wayback,
        timestamp=_timestamp_from_snapshot(snapshot_url),
        url=snapshot_url,
    )
    _save_technologies(result.get("technologies", []), snapshot=snapshot)

    return analysis


@transaction.atomic
def persist_history(result: dict, *, duration_ms: int | None = None) -> Analysis:
    """
    Persiste el análisis histórico: un Analysis (triggered_by='historical') con un
    WaybackResult que agrupa las ~12 capturas, cada una con sus tecnologías.
    Mapea 1:1 con el ERD: WaybackResult -> WaybackSnapshot -> Technology.
    """
    domain, _ = Domain.objects.get_or_create(name=extract_domain(result["url"]))
    analysis = Analysis.objects.create(
        domain=domain, source_url=result["url"],
        status="completed", triggered_by="historical", duration_ms=duration_ms,
    )

    snapshots  = result.get("snapshots", [])
    timestamps = sorted(s["timestamp"] for s in snapshots if s.get("timestamp"))
    wayback = WaybackResult.objects.create(
        analysis=analysis,
        snapshot_count=len(snapshots),
        archive_pages=result.get("archive_pages"),
        first_snapshot_at=_parse_ts(timestamps[0]) if timestamps else None,
        last_snapshot_at=_parse_ts(timestamps[-1]) if timestamps else None,
    )
    for snap in snapshots:
        ws = WaybackSnapshot.objects.create(
            wayback_result=wayback,
            timestamp=snap.get("timestamp", ""),
            url=snap.get("url", ""),
        )
        _save_technologies(snap.get("technologies", []), snapshot=ws)

    return analysis


# ── helpers de escritura ──────────────────────────────────────────────────────

def _save_technologies(techs, *, analysis=None, snapshot=None):
    Technology.objects.bulk_create([
        Technology(
            analysis=analysis, snapshot=snapshot,
            name=t["name"], category=t.get("category", ""),
            version=t.get("version"),
            confidence=t.get("confidence", 0), evidence=t.get("evidence", ""),
        )
        for t in techs
    ])


def _save_whois(analysis, whois):
    if not whois:
        _log_error(analysis, "whois", "WHOIS lookup returned no data")
        return
    WhoisRecord.objects.create(
        analysis=analysis,
        registrar=whois.get("registrar"),
        registrant=whois.get("registrant"),
        creation_date=_parse_dt(whois.get("creation_date")),
        expiration_date=_parse_dt(whois.get("expiration_date")),
        domain_age_years=whois.get("domain_age_years"),
    )


def _save_geo(analysis, geo):
    if not geo:
        _log_error(analysis, "geo", "Geo lookup returned no data")
        return
    GeoRecord.objects.create(
        analysis=analysis,
        country=geo.get("country"), country_code=geo.get("countryCode"),
        city=geo.get("city"), region=geo.get("regionName"),
        isp=geo.get("isp"), org=geo.get("org"),
        ip_address=geo.get("ip"), latitude=geo.get("lat"),
        longitude=geo.get("lon"), asn=geo.get("as"),
    )


def _save_dns(analysis, dns):
    if not dns:
        _log_error(analysis, "dns", "DNS lookup returned no data")
        return
    dns_result = DnsResult.objects.create(analysis=analysis)
    rows = []
    for record_type, values in dns.items():
        for value in values:
            priority = None
            if record_type == "MX" and " " in value:
                prio, _, host = value.partition(" ")
                if prio.isdigit():
                    priority, value = int(prio), host
            rows.append(DnsRecord(
                dns_result=dns_result, record_type=record_type,
                value=value, priority=priority,
            ))
    DnsRecord.objects.bulk_create(rows)


def _save_wayback(analysis, wayback):
    if not wayback:
        _log_error(analysis, "wayback", "Wayback lookup returned no data")
        return
    persist_wayback(analysis, wayback)


@transaction.atomic
def persist_wayback(analysis: Analysis, wayback: dict) -> WaybackResult:
    """
    Adjunta el resultado de Wayback a un análisis existente (carga diferida).
    Devuelve el WaybackResult creado para serializarlo en la respuesta.
    """
    snapshots = wayback.get("snapshots", [])
    timestamps = sorted(s["timestamp"] for s in snapshots if s.get("timestamp"))
    result = WaybackResult.objects.create(
        analysis=analysis,
        snapshot_count=len(snapshots),
        archive_pages=wayback.get("archive_pages"),
        first_snapshot_at=_parse_ts(timestamps[0]) if timestamps else None,
        last_snapshot_at=_parse_ts(timestamps[-1]) if timestamps else None,
    )
    WaybackSnapshot.objects.bulk_create([
        WaybackSnapshot(wayback_result=result, timestamp=s.get("timestamp", ""), url=s.get("url", ""))
        for s in snapshots
    ])
    return result


def _log_error(analysis, service, message):
    AnalysisError.objects.create(analysis=analysis, service=service, message=message)


# ── helpers de parsing ────────────────────────────────────────────────────────

def _parse_dt(value):
    """Parsea una fecha WHOIS (str) a datetime aware; None si no se puede."""
    if not value or value == "None":
        return None
    from django.utils.dateparse import parse_datetime, parse_date
    dt = parse_datetime(value)
    if dt:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    d = parse_date(value)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) if d else None


def _parse_ts(ts):
    """Timestamp Wayback '19970501011626' → datetime aware."""
    try:
        return datetime.strptime(ts, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _original_url_from_snapshot(snapshot_url: str) -> str:
    # https://web.archive.org/web/20230101000000/https://github.com/ -> https://github.com/
    match = re.search(r"/web/\d+(?:[a-z_]+)?/(.*)$", snapshot_url)
    return match.group(1) if match else snapshot_url


def _timestamp_from_snapshot(snapshot_url: str) -> str:
    match = re.search(r"/web/(\d+)", snapshot_url)
    return match.group(1) if match else ""
