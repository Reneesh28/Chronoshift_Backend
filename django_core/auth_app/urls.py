from django.urls import path

from .views import (
    health_check,
    register_user,
    login_user,
    refresh_access_token,
    logout_user,
    profile,
)

urlpatterns = [
    path("health/", health_check),

    path("register/", register_user, name="register"),
    path("login/", login_user, name="login"),

    path("refresh/", refresh_access_token, name="refresh"),
    path("logout/", logout_user, name="logout"),

    path("profile/", profile, name="profile"),
]