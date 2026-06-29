from django.db import models


class Analysis(models.Model):
    """
    Resultado persistido de un análisis de tecnologías (RF-09).

    Guarda la salida del Analyzer tal cual: las tecnologías detectadas y los
    bloques de infraestructura (DNS, WHOIS, Geo, Wayback) como JSON, para poder
    recuperarlos (RF-10), compararlos (RF-11) y agregarlos en estadísticas
    (RF-12, RF-13) sin re-analizar el sitio.
    """

    url          = models.URLField(max_length=2000)
    technologies = models.JSONField(default=list)
    dns          = models.JSONField(null=True, blank=True)
    whois        = models.JSONField(null=True, blank=True)
    geo          = models.JSONField(null=True, blank=True)
    wayback      = models.JSONField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "analyses"

    def __str__(self) -> str:
        return f"Analysis #{self.pk} — {self.url}"

    @classmethod
    def from_result(cls, result: dict) -> "Analysis":
        """Crea (sin guardar aún se decide afuera) una instancia desde el dict del Analyzer."""
        return cls(
            url=result.get("url", ""),
            technologies=result.get("technologies", []),
            dns=result.get("dns"),
            whois=result.get("whois"),
            geo=result.get("geo"),
            wayback=result.get("wayback"),
        )

    def to_dict(self) -> dict:
        """Reconstruye el envelope de datos para las respuestas GET."""
        return {
            "id":           self.pk,
            "url":          self.url,
            "technologies": self.technologies,
            "dns":          self.dns,
            "whois":        self.whois,
            "geo":          self.geo,
            "wayback":      self.wayback,
            "created_at":   self.created_at.isoformat(),
        }
