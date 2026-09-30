from django.urls import path

from executions.views import ExecutionCreateView, ExecutionDetailView

urlpatterns = [
    path("", ExecutionCreateView.as_view()),
    path("<str:execution_id>/", ExecutionDetailView.as_view()),
]
