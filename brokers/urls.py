from django.urls import path

from brokers.views import BrokerCallbackView, BrokerListView, BrokerLoginView

urlpatterns = [
    path("", BrokerListView.as_view()),
    path("<str:broker>/login/", BrokerLoginView.as_view()),
    path("<str:broker>/callback/", BrokerCallbackView.as_view()),
]
