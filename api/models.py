"""
Modelo relacional normalizado del Workshop #2 (sección 5).

Decisiones tomadas para corregir ambigüedades/errores del ERD original:
  * Technology colgaba SOLO de WaybackSnapshot, dejando sin lugar a las
    tecnologías de un análisis en vivo. Aquí Technology tiene dos FKs opcionales
    (analysis / snapshot) y un CheckConstraint que obliga a exactamente un padre.
  * WaybackSnapshot tenía un campo `technologies` redundante con la entidad
    Technology. Se elimina; las tecnologías viven normalizadas en Technology.
  * `category` ahora incluye "server" (ServerDetector se agregó después del ERD).
  * Se agrega `Analysis.source_url` para conservar la URL exacta analizada
    (el ERD solo guardaba el Domain, perdiendo path y el caso snapshot).
"""
from django.db import models
from django.db.models import Q


class Domain(models.Model):
    """Un dominio analizable; agrupa múltiples análisis a lo largo del tiempo."""
    name          = models.CharField(max_length=255, unique=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Analysis(models.Model):
    STATUS_CHOICES = [("completed", "completed"), ("partial", "partial"), ("failed", "failed")]
    TRIGGER_CHOICES = [("api", "api"), ("snapshot", "snapshot"), ("cli", "cli")]

    domain       = models.ForeignKey(Domain, related_name="analyses", on_delete=models.CASCADE)
    source_url   = models.URLField(max_length=2000)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    triggered_by = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="api")
    duration_ms  = models.PositiveIntegerField(null=True, blank=True)
    analyzed_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-analyzed_at"]
        verbose_name_plural = "analyses"

    def __str__(self) -> str:
        return f"Analysis #{self.pk} — {self.source_url}"

    def to_dict(self) -> dict:
        return {
            "id":           self.pk,
            "url":          self.source_url,
            "domain":       self.domain.name,
            "status":       self.status,
            "triggered_by": self.triggered_by,
            "duration_ms":  self.duration_ms,
            "analyzed_at":  self.analyzed_at.isoformat(),
            "technologies": [t.to_dict() for t in self.technologies.all()],
            "dns":          _safe(lambda: self.dns_result.to_dict()),
            "whois":        _safe(lambda: self.whois_record.to_dict()),
            "geo":          _safe(lambda: self.geo_record.to_dict()),
            "wayback":      _safe(lambda: self.wayback_result.to_dict()),
            "errors":       [e.to_dict() for e in self.errors.all()],
            "tags":         {t.key: t.value for t in self.tags.all()},
        }


class WhoisRecord(models.Model):
    analysis         = models.OneToOneField(Analysis, related_name="whois_record", on_delete=models.CASCADE)
    registrar        = models.CharField(max_length=255, null=True, blank=True)
    registrant       = models.CharField(max_length=255, null=True, blank=True)
    creation_date    = models.DateTimeField(null=True, blank=True)
    expiration_date  = models.DateTimeField(null=True, blank=True)
    updated_date     = models.DateTimeField(null=True, blank=True)
    domain_age_years = models.FloatField(null=True, blank=True)
    status_flags     = models.JSONField(null=True, blank=True)

    def to_dict(self) -> dict:
        return {
            "registrar":        self.registrar,
            "registrant":       self.registrant,
            "creation_date":    self.creation_date.isoformat() if self.creation_date else None,
            "expiration_date":  self.expiration_date.isoformat() if self.expiration_date else None,
            "domain_age_years": self.domain_age_years,
        }


class GeoRecord(models.Model):
    analysis     = models.OneToOneField(Analysis, related_name="geo_record", on_delete=models.CASCADE)
    country      = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=8, null=True, blank=True)
    city         = models.CharField(max_length=100, null=True, blank=True)
    region       = models.CharField(max_length=100, null=True, blank=True)
    isp          = models.CharField(max_length=255, null=True, blank=True)
    org          = models.CharField(max_length=255, null=True, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)
    latitude     = models.FloatField(null=True, blank=True)
    longitude    = models.FloatField(null=True, blank=True)
    asn          = models.CharField(max_length=100, null=True, blank=True)

    def to_dict(self) -> dict:
        return {
            "country": self.country, "city": self.city, "isp": self.isp,
            "org": self.org, "ip": self.ip_address,
            "lat": self.latitude, "lon": self.longitude,
        }


class DnsResult(models.Model):
    analysis = models.OneToOneField(Analysis, related_name="dns_result", on_delete=models.CASCADE)
    resolver = models.CharField(max_length=100, null=True, blank=True)

    def to_dict(self) -> dict:
        # Reconstruye el dict {tipo: [valores]} desde las filas normalizadas.
        records: dict[str, list] = {}
        for r in self.records.all():
            records.setdefault(r.record_type, []).append(r.value)
        return records


class DnsRecord(models.Model):
    dns_result  = models.ForeignKey(DnsResult, related_name="records", on_delete=models.CASCADE)
    record_type = models.CharField(max_length=10)
    value       = models.CharField(max_length=500)
    ttl         = models.PositiveIntegerField(null=True, blank=True)
    priority    = models.PositiveIntegerField(null=True, blank=True)


class WaybackResult(models.Model):
    analysis          = models.OneToOneField(Analysis, related_name="wayback_result", on_delete=models.CASCADE)
    snapshot_count    = models.PositiveIntegerField(default=0)   # nº de snapshots realmente almacenados
    archive_pages     = models.PositiveIntegerField(null=True, blank=True)  # páginas CDX (métrica de volumen)
    first_snapshot_at = models.DateTimeField(null=True, blank=True)
    last_snapshot_at  = models.DateTimeField(null=True, blank=True)

    def to_dict(self) -> dict:
        return {
            "snapshot_count":    self.snapshot_count,
            "archive_pages":     self.archive_pages,
            "first_snapshot_at": self.first_snapshot_at.isoformat() if self.first_snapshot_at else None,
            "last_snapshot_at":  self.last_snapshot_at.isoformat() if self.last_snapshot_at else None,
            "snapshots":         [s.to_dict() for s in self.snapshots.all()],
        }


class WaybackSnapshot(models.Model):
    wayback_result = models.ForeignKey(WaybackResult, related_name="snapshots", on_delete=models.CASCADE)
    timestamp      = models.CharField(max_length=20)
    url            = models.URLField(max_length=2000)
    http_status    = models.PositiveIntegerField(null=True, blank=True)

    def to_dict(self) -> dict:
        return {
            "timestamp":    self.timestamp,
            "url":          self.url,
            "technologies": [t.to_dict() for t in self.technologies.all()],
        }


class Technology(models.Model):
    CATEGORY_CHOICES = [
        ("frontend", "frontend"), ("backend", "backend"),
        ("cdn", "cdn"), ("server", "server"),
    ]
    # Exactamente uno de estos dos padres está set (ver CheckConstraint).
    analysis    = models.ForeignKey(Analysis, related_name="technologies", null=True, blank=True, on_delete=models.CASCADE)
    snapshot    = models.ForeignKey(WaybackSnapshot, related_name="technologies", null=True, blank=True, on_delete=models.CASCADE)
    name        = models.CharField(max_length=100)
    category    = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    version     = models.CharField(max_length=50, null=True, blank=True)
    confidence  = models.PositiveIntegerField(default=0)
    evidence    = models.TextField(blank=True, default="")
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="technology_exactly_one_parent",
                condition=(
                    (Q(analysis__isnull=False) & Q(snapshot__isnull=True))
                    | (Q(analysis__isnull=True) & Q(snapshot__isnull=False))
                ),
            )
        ]

    def to_dict(self) -> dict:
        return {
            "name":       self.name,
            "category":   self.category,
            "confidence": self.confidence,
            "evidence":   self.evidence,
        }


class AnalysisError(models.Model):
    analysis    = models.ForeignKey(Analysis, related_name="errors", on_delete=models.CASCADE)
    service     = models.CharField(max_length=50)
    error_code  = models.CharField(max_length=50, null=True, blank=True)
    message     = models.TextField(blank=True, default="")
    occurred_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self) -> dict:
        return {"service": self.service, "code": self.error_code, "message": self.message}


class AnalysisTag(models.Model):
    analysis = models.ForeignKey(Analysis, related_name="tags", on_delete=models.CASCADE)
    key      = models.CharField(max_length=100)
    value    = models.CharField(max_length=255, blank=True, default="")


# ── helpers ───────────────────────────────────────────────────────────────────

def _safe(getter):
    """Devuelve getter() o None si la relación 1:1 inversa no existe."""
    from django.core.exceptions import ObjectDoesNotExist
    try:
        return getter()
    except ObjectDoesNotExist:
        return None
