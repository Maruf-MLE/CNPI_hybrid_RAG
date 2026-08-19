"""URL routes for the admin_panel app."""

from django.urls import path
from . import views

urlpatterns = [
    # Login / Logout
    path("login/", views.login_view, name="admin-panel-login"),
    path("logout/", views.logout_view, name="admin-panel-logout"),

    # Main page — login না থাকলে redirect হবে
    path("", views.index_view, name="admin-panel-index"),

    # API — documents
    path("api/search/", views.search_view, name="admin-panel-search"),
    path("api/document/", views.document_view, name="admin-panel-document"),
    path("api/update/", views.update_view, name="admin-panel-update"),
    path("api/create/", views.create_view, name="admin-panel-create"),
    path("api/stats/", views.stats_view, name="admin-panel-stats"),

    # API — captains
    path("api/captains/", views.captains_list_view, name="admin-panel-captains-list"),
    path("api/captains/create/", views.captain_create_view, name="admin-panel-captain-create"),
    path("api/captains/update/", views.captain_update_view, name="admin-panel-captain-update"),
    path("api/captains/deactivate/", views.captain_deactivate_view, name="admin-panel-captain-deactivate"),
    path("api/captains/stats/", views.captain_stats_view, name="admin-panel-captain-stats"),
]
