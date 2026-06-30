from django.urls import path

from api import views

app_name = "api"

urlpatterns = [
    path("analyses/", views.AnalysisCreateView.as_view(), name="analysis-create"),
    path("ai-analyses/", views.AIAnalysisCreateView.as_view(), name="ai-analysis-create"),
    path("analyses/snapshot/", views.SnapshotAnalysisView.as_view(), name="analysis-snapshot"),
    path("analyses/historical/", views.HistoricalAnalysisView.as_view(), name="analysis-historical"),
    path("analyses/compare/", views.AnalysisCompareView.as_view(), name="analysis-compare"),
    path("analyses/<int:pk>/wayback/", views.AnalysisWaybackView.as_view(), name="analysis-wayback"),
    path("analyses/<int:pk>/", views.AnalysisDetailView.as_view(), name="analysis-detail"),
    path("domains/<str:name>/analyses/", views.DomainHistoryView.as_view(), name="domain-history"),
    path("stats/", views.StatsView.as_view(), name="stats"),
]
