from django.urls import path
from .views import health_check, start_replay, get_replay_status

urlpatterns = [
    path("health/", health_check),
    path("start/", start_replay),
    path("status/<str:replay_id>/", get_replay_status),
]