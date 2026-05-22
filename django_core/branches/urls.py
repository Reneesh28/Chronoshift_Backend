from django.urls import path
from .views import (
    health_check,
    create_branch,
    get_branch_details,
    inject_decision_event,
    compare_branches
)

urlpatterns = [
    path("health/", health_check),
    path("", create_branch),
    path("create/", create_branch),
    path("compare/", compare_branches),
    path("events/", inject_decision_event),
    path("<str:branch_id>/", get_branch_details),
]