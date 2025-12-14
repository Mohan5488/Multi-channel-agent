from rest_framework import serializers
from django.contrib.auth.models import User

class UserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "password"]

    def validate(self, data):
        if User.objects.filter(username = data["username"]).exists():
            serializers.ValidationError("user already exists")
        return data

    def create(self, validated_data):
        user = User(username = validated_data["username"])
        user.set_password(validated_data['password'])

        user.save()
        return user
    