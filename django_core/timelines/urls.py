from django.urls import path

from .views import (
    health_check,
    create_timeline,
    list_timelines,
    timeline_detail,
    update_timeline,
    delete_timeline,
)

urlpatterns = [
    path("health/", health_check),

    # CREATE + LIST
    path("create/", create_timeline),
    path("", list_timelines),

    # DETAIL
    path("<str:timeline_id>/", timeline_detail),

    # UPDATE
    path("<str:timeline_id>/update/", update_timeline),

    # DELETE
    path("<str:timeline_id>/delete/", delete_timeline),
]