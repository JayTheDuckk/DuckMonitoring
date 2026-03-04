from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'is_active', 'date_joined', 'last_login', 'is_staff', 'is_superuser')
        read_only_fields = ('id', 'date_joined', 'last_login', 'is_staff', 'is_superuser')

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if instance.role == 'admin':
            instance.is_staff = True
            instance.is_superuser = True
        else:
            instance.is_staff = False
            instance.is_superuser = False
        instance.save()
        return instance

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'role')
        
    def create(self, validated_data):
        # Auto-promote first user to Admin
        is_first_user = not User.objects.exists()
        role = 'admin' if is_first_user else validated_data.get('role', 'viewer')
        
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            role=role
        )
        user.set_password(validated_data['password'])
        
        if is_first_user:
            user.is_staff = True
            user.is_superuser = True
            
        user.save()
        return user

from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = '__all__'
