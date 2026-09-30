from django.contrib import admin
from django.urls import include, path

from common.views import TokenView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", TokenView.as_view()),
    path("api/brokers/", include("brokers.urls")),
]
