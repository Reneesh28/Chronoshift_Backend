from django.contrib import admin
from django.urls import path, include
from branches.views import inject_decision_event, compare_branches

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/auth/", include("auth_app.urls")),
    path("api/timelines/", include("timelines.urls")),
    path("api/branches/", include("branches.urls")),
    path("api/replay/", include("replay.urls")),
    path("api/events/", inject_decision_event),
    path("api/compare/", compare_branches),
]