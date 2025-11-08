# serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User
from .serializers import UserSerializer  

class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer to obtain JWT tokens using email instead of username.
    Returns access, refresh tokens, and serialized user data.
    """
    username_field = "email"

    def validate(self, attrs):
        credentials = {
            "email": attrs.get("email"),
            "password": attrs.get("password"),
        }

        user = authenticate(**credentials)
        if not user:
            raise serializers.ValidationError("Invalid email or password")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled")

        data = super().validate(attrs)

        data["user"] = UserSerializer(user).data
        return data
