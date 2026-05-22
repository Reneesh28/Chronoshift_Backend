from django.contrib.auth.models import User
from rest_framework import serializers
from utils.mongo import users_collection


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password"]

    def validate_username(self, value):
        # 1. Check uniqueness in Django SQLite Auth
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists in auth database.")

        # 2. Check uniqueness in MongoDB Atlas
        if users_collection.find_one({"username": value}):
            raise serializers.ValidationError("A user profile with that username already exists in MongoDB Atlas.")

        return value

    def validate_email(self, value):
        if not value:
            return value

        # 1. Check uniqueness in Django SQLite Auth
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists in auth database.")

        # 2. Check uniqueness in MongoDB Atlas
        if users_collection.find_one({"email": value}):
            raise serializers.ValidationError("A user profile with that email already exists in MongoDB Atlas.")

        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"]
        )
        return user