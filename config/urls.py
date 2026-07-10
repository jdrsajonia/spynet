from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.urls")),
]

handler404 = "api.utils.exception_handler.handler404"
handler500 = "api.utils.exception_handler.handler500"