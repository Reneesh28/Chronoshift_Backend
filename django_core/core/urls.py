from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api-auth/", include("rest_framework.urls")),
    path("api/auth/", include("auth_app.urls")),
    path("api/timelines/", include("timelines.urls")),
    path("api/branches/", include("branches.urls")),
    path("api/replay/", include("replay.urls")),
]