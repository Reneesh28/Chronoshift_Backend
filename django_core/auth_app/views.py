from django.contrib.auth.models import User

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import (
    IsAuthenticated,
    AllowAny,
)
from rest_framework.response import Response
from rest_framework import status

from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer
from utils.mongo import users_collection


# HEALTH CHECK
@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):

    return Response({
        "service": "auth_app",
        "status": "running"
    })


# REGISTER
@api_view(["POST"])
@permission_classes([AllowAny])
def register_user(request):

    serializer = RegisterSerializer(data=request.data)

    if serializer.is_valid():

        user = serializer.save()

        # STORE IN MONGODB
        try:
            users_collection.insert_one({
                "username": user.username,
                "email": user.email,
                "password_hash": user.password,
            })
        except Exception as e:
            user.delete()
            return Response({
                "error": f"Failed to persist user profile in MongoDB Atlas: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        refresh = RefreshToken.for_user(user)

        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        response = Response({
            "message": "User registered successfully",
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            }
        }, status=status.HTTP_201_CREATED)

        # HTTP-ONLY REFRESH COOKIE

        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,  # True in production HTTPS
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


# LOGIN

@api_view(["POST"])
@permission_classes([AllowAny])
def login_user(request):

    username = request.data.get("username")
    password = request.data.get("password")

    try:
        user = User.objects.get(username=username)

    except User.DoesNotExist:

        return Response({
            "error": "Invalid credentials"
        }, status=status.HTTP_401_UNAUTHORIZED)

    if not user.check_password(password):

        return Response({
            "error": "Invalid credentials"
        }, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)

    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    response = Response({
        "message": "Login successful",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
        }
    })

    # HTTP-ONLY REFRESH COOKIE

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,  # True in production HTTPS
        samesite="Lax",
        max_age=7 * 24 * 60 * 60,
    )

    return response


# --------------------------------------------------
# REFRESH ACCESS TOKEN
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_access_token(request):

    old_refresh_token = request.COOKIES.get("refresh_token")

    if not old_refresh_token:

        return Response({
            "error": "Refresh token missing"
        }, status=status.HTTP_401_UNAUTHORIZED)

    try:
        old_refresh = RefreshToken(old_refresh_token)

        user_id = old_refresh["user_id"]

        user = User.objects.get(id=user_id)
        # ROTATE TOKENS

        new_refresh = RefreshToken.for_user(user)

        new_access_token = str(new_refresh.access_token)
        new_refresh_token = str(new_refresh)

        response = Response({
            "access_token": new_access_token
        })

        # SET NEW REFRESH COOKIE

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            secure=False,  # True in production HTTPS
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )

        return response

    except Exception:

        return Response({
            "error": "Invalid refresh token"
        }, status=status.HTTP_401_UNAUTHORIZED)


# LOGOUT
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_user(request):

    response = Response({
        "message": "Logged out successfully"
    })

    response.delete_cookie("refresh_token")

    return response


# PROFILE

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):

    user = request.user

    return Response({
        "id": user.id,
        "username": user.username,
        "email": user.email,
    })