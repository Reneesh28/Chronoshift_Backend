from django.contrib import admin
from django.urls import path, include, re_path
from branches.views import inject_decision_event, compare_branches
from core.proxy_views import proxy_to_simulator, proxy_to_ai_engine

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/auth/", include("auth_app.urls")),
    path("api/timelines/", include("timelines.urls")),
    path("api/branches/", include("branches.urls")),
    path("api/replay/", include("replay.urls")),
    path("api/events/", inject_decision_event),
    path("api/compare/", compare_branches),
    
    # Unified Monolith Proxy Endpoints
    re_path(r"^api/simulator/(?P<path>.*)$", proxy_to_simulator),
    re_path(r"^api/ai/(?P<path>.*)$", proxy_to_ai_engine),
]