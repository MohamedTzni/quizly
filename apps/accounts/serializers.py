from django.contrib.auth.models import User
from rest_framework import serializers


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    confirmed_password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "confirmed_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        """Checks that password and confirmation match."""
        if data["password"] != data["confirmed_password"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def validate_email(self, value):
        """Checks that the email is not already taken."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def create(self, validated_data):
        """Creates a new user with a hashed password."""
        validated_data.pop("confirmed_password")
        return User.objects.create_user(**validated_data)
