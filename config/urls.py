from django.contrib import admin
from django.urls import include, path

from common.views import TokenView, frontend

urlpatterns = [
    path("", frontend),
    path("admin/", admin.site.urls),
    path("api/auth/token/", TokenView.as_view()),
    path("api/brokers/", include("brokers.urls")),
    path("api/executions/", include("executions.urls")),
]

handler404 = "common.views.not_found"
handler500 = "common.views.server_error"
