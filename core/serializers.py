from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    User, Role, Permission, UserRole, ResourceType,
    Resource, ResourceAccess, AuditLog
)
import re


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,
        error_messages={
            'min_length': 'Пароль должен содержать минимум 8 символов'
        }
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'first_name', 'last_name', 'patronymic')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value
    
    def validate_password(self, value):
        # Проверка сложности пароля
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну заглавную букву")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну строчную букву")
        if not re.search(r'\d', value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну цифру")
        return value
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Пароли не совпадают"})
        return data
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False,
        write_only=True
    )
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                msg = _('Неверный email или пароль')
                raise serializers.ValidationError(msg, code='authorization')
            
            # Проверяем пароль с помощью check_password
            if not user.check_password(password):
                msg = _('Неверный email или пароль')
                raise serializers.ValidationError(msg, code='authorization')
            
            if not user.is_active:
                msg = _('Аккаунт деактивирован')
                raise serializers.ValidationError(msg, code='authorization')
            
            data['user'] = user
        else:
            msg = _('Необходимо указать email и пароль')
            raise serializers.ValidationError(msg, code='authorization')
        
        return data


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'first_name', 'last_name', 'patronymic',
            'full_name', 'is_active', 'date_joined', 'last_login',
            'roles'
        )
        read_only_fields = ('id', 'email', 'is_active', 'date_joined', 'last_login')
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_roles(self, obj):
        return [role.role.name for role in obj.user_roles.all()]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'patronymic')
    
    def update(self, instance, validated_data):
        # Логируем изменение профиля
        from .utils import log_action
        log_action(
            user=self.context['request'].user,
            action='update',
            resource_type='user',
            resource_id=str(instance.id),
            details={'updated_fields': list(validated_data.keys())}
        )
        return super().update(instance, validated_data)


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'codename', 'name', 'resource_type', 'action', 'description')


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permissions_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Role
        fields = ('id', 'name', 'code', 'description', 'is_admin', 'permissions', 'permissions_ids')
    
    def create(self, validated_data):
        permissions_ids = validated_data.pop('permissions_ids', [])
        role = Role.objects.create(**validated_data)
        
        if permissions_ids:
            permissions = Permission.objects.filter(id__in=permissions_ids)
            role.permissions.set(permissions)
        
        return role
    
    def update(self, instance, validated_data):
        permissions_ids = validated_data.pop('permissions_ids', None)
        role = super().update(instance, validated_data)
        
        if permissions_ids is not None:
            permissions = Permission.objects.filter(id__in=permissions_ids)
            role.permissions.set(permissions)
        
        return role


class UserRoleSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = UserRole
        fields = ('id', 'user', 'role', 'user_email', 'role_name',
                 'assigned_at', 'assigned_by', 'resource_scope')
        read_only_fields = ('assigned_at', 'assigned_by')
    
    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)


class ResourceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceType
        fields = ('id', 'name', 'code', 'description')


class ResourceSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    resource_type_name = serializers.CharField(source='resource_type.name', read_only=True)
    
    class Meta:
        model = Resource
        fields = (
            'id', 'name', 'description', 'resource_type', 'resource_type_name',
            'owner', 'owner_email', 'metadata', 'created_at', 'updated_at',
            'is_active'
        )
        read_only_fields = ('owner', 'created_at', 'updated_at')
    
    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class ResourceAccessSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    resource_name = serializers.CharField(source='resource.name', read_only=True)
    permission_name = serializers.CharField(source='permission.name', read_only=True)
    
    class Meta:
        model = ResourceAccess
        fields = (
            'id', 'user', 'resource', 'permission', 'user_email',
            'resource_name', 'permission_name', 'granted_at',
            'granted_by', 'conditions', 'expires_at'
        )
        read_only_fields = ('granted_at', 'granted_by')
    
    def validate(self, data):
        # Проверяем, что у пользователя есть доступ на предоставление такого разрешения
        request_user = self.context['request'].user
        permission = data.get('permission')
        
        if permission and not request_user.has_perm(f'core.{permission.codename}'):
            raise serializers.ValidationError(
                "У вас нет прав на предоставление этого разрешения"
            )
        
        return data
    
    def create(self, validated_data):
        validated_data['granted_by'] = self.context['request'].user
        return super().create(validated_data)


class AuditLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = (
            'id', 'user', 'user_email', 'action', 'resource_type',
            'resource_id', 'details', 'ip_address', 'user_agent',
            'timestamp'
        )
        read_only_fields = fields