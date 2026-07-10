from django.contrib import admin

from api.models import (
    Analysis,
    AnalysisError,
    AnalysisTag,
    DnsRecord,
    DnsResult,
    Domain,
    GeoRecord,
    Technology,
    WaybackResult,
    WaybackSnapshot,
    WhoisRecord,
)


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ("id", "domain", "analyzed_at")
    list_filter = ("analyzed_at",)
    search_fields = ("domain__name",)


@admin.register(WhoisRecord)
class WhoisRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis")


@admin.register(GeoRecord)
class GeoRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis")


@admin.register(DnsResult)
class DnsResultAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis")


@admin.register(DnsRecord)
class DnsRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "dns_result")


@admin.register(WaybackResult)
class WaybackResultAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis")


@admin.register(WaybackSnapshot)
class WaybackSnapshotAdmin(admin.ModelAdmin):
    list_display = ("id", "wayback_result")


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "analysis")
    search_fields = ("name",)


@admin.register(AnalysisError)
class AnalysisErrorAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis")


@admin.register(AnalysisTag)
class AnalysisTagAdmin(admin.ModelAdmin):
    list_display = ("id", "analysis")