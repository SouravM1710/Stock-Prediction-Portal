from django.contrib.auth.models import User
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    class Meta:
        model = User
        fields = ['username', 'email', 'password'] 

    def create(self, validated_data):
        # User.objects.create_user handles password hashing
        # User.objects.create saves password in plain text (not secure)
        user = User.objects.create_user(
            validated_data['username'],
            validated_data['email'],
            validated_data['password']
        )
        # user = User.objects.create_user(**validated_data) # use only when you have mandetory feilds
        return user