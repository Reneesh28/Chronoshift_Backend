from django.urls import path
from .views import health_check, start_replay, get_replay_status, get_replay_details

urlpatterns = [
    path("health/", health_check),
    path("start/", start_replay),
    path("status/<str:replay_id>/", get_replay_status),
    path("details/<str:replay_id>/", get_replay_details),
]