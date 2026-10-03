from django.urls import path

from messenger_bot import views

urlpatterns = [
    path("webhook/", views.webhook_view, name="messenger-webhook"),
]
