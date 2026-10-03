"""
URL configuration for cnpi_api project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("rag_api.urls")),
    path("admin-panel/", include("admin_panel.urls")),
    # Facebook Messenger webhook — must be at root so Meta can reach it
    # without any auth middleware or session checks blocking the request.
    path("", include("messenger_bot.urls")),
    # Redirect /admin000 to admin panel
    path("admin000/", RedirectView.as_view(url="/admin-panel/", permanent=False)),
]
