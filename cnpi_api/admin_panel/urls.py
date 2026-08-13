"""URL routes for the admin_panel app."""

from django.urls import path
from . import views

urlpatterns = [
    # Login / Logout
    path("login/", views.login_view, name="admin-panel-login"),
    path("logout/", views.logout_view, name="admin-panel-logout"),

    # Main page — login না থাকলে redirect হবে
    path("", views.index_view, name="admin-panel-index"),

    # API
    path("api/search/", views.search_view, name="admin-panel-search"),
    path("api/document/", views.document_view, name="admin-panel-document"),
    path("api/update/", views.update_view, name="admin-panel-update"),
    path("api/create/", views.create_view, name="admin-panel-create"),
    path("api/stats/", views.stats_view, name="admin-panel-stats"),
]
