from django.urls import path

from messenger_bot import views

urlpatterns = [
    # Both with and without trailing slash — Meta sometimes drops the slash
    # in redirect chains, so we handle both directly without APPEND_SLASH redirect.
    path("webhook/", views.webhook_view, name="messenger-webhook"),
    path("webhook", views.webhook_view, name="messenger-webhook-noslash"),
]
