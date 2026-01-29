from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from .models import Permission as CustomPermission, UserRole, ResourceAccess, Resource
from django.utils import timezone


class IsAuthenticated(permissions.BasePermission):
    """
    Разрешение для проверки аутентификации.
    Возвращает 401 если пользователь не аутентифицирован.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise AuthenticationFailed(
                'Аутентификация не пройдена',
                code='not_authenticated'
            )
        return True


class HasPermission(permissions.BasePermission):
    """
    Проверяет, есть ли у пользователя конкретное разрешение.
    """
    def __init__(self, permission_codename):
        self.permission_codename = permission_codename
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Администраторы имеют все права
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Проверяем наличие разрешения у пользователя
        return self._check_user_permission(request.user, self.permission_codename)
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # Если объект является ресурсом, проверяем доступ к нему
        if isinstance(obj, Resource):
            return self._check_resource_permission(
                request.user,
                obj,
                self.permission_codename
            )
        
        return self._check_user_permission(request.user, self.permission_codename)
    
    def _check_user_permission(self, user, permission_codename):
        # Проверяем разрешения через роли пользователя
        user_roles = UserRole.objects.filter(user=user)
        
        for user_role in user_roles:
            # Проверяем разрешения роли
            role_permissions = user_role.role.permissions.filter(
                codename=permission_codename
            )
            
            if role_permissions.exists():
                # Проверяем условия
                role_permission = user_role.role_permissions.filter(
                    permission__codename=permission_codename
                ).first()
                
                if role_permission:
                    conditions = role_permission.conditions
                    if self._check_conditions(user, conditions):
                        return True
        
        # Проверяем прямые разрешения пользователя
        direct_permissions = user.resource_accesses.filter(
            permission__codename=permission_codename,
            expires_at__gt=timezone.now()
        )
        
        for access in direct_permissions:
            if not access.is_expired() and self._check_conditions(user, access.conditions):
                return True
        
        return False
    
    def _check_resource_permission(self, user, resource, permission_codename):
        # Проверяем, является ли пользователь владельцем
        if resource.owner == user:
            return True
        
        # Проверяем доступ через роли с учетом области действия
        user_roles = UserRole.objects.filter(user=user)
        
        for user_role in user_roles:
            # Проверяем область действия роли
            resource_scope = user_role.resource_scope
            if self._check_resource_scope(resource, resource_scope):
                # Проверяем разрешения роли для этого типа ресурса
                role_permissions = user_role.role.permissions.filter(
                    codename=permission_codename,
                    resource_type=resource.resource_type
                )
                
                if role_permissions.exists():
                    return True
        
        # Проверяем прямой доступ к ресурсу
        direct_access = ResourceAccess.objects.filter(
            user=user,
            resource=resource,
            permission__codename=permission_codename,
            expires_at__gt=timezone.now()
        ).exists()
        
        return direct_access
    
    def _check_conditions(self, user, conditions):
        """Проверяет условия доступа"""
        if not conditions:
            return True
        
        # Пример проверки условий (можно расширять)
        if 'time_restriction' in conditions:
            # Проверка временных ограничений
            pass
        
        if 'department' in conditions:
            # Проверка отдела
            pass
        
        return True
    
    def _check_resource_scope(self, resource, resource_scope):
        """Проверяет область действия роли для ресурса"""
        if not resource_scope:
            return True
        
        # Пример: проверка по типу ресурса
        if 'resource_types' in resource_scope:
            allowed_types = resource_scope['resource_types']
            if str(resource.resource_type.id) not in allowed_types:
                return False
        
        # Пример: проверка по владельцу
        if 'owner_department' in resource_scope:
            # Проверка отдела владельца
            pass
        
        return True


class IsAdmin(permissions.BasePermission):
    """Проверяет, является ли пользователь администратором"""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Проверяем суперпользователя
        if request.user.is_superuser:
            return True
        
        # Проверяем администраторскую роль
        return request.user.user_roles.filter(role__is_admin=True).exists()


class IsOwnerOrHasPermission(permissions.BasePermission):
    """
    Разрешает доступ владельцу или пользователю с определенным разрешением.
    """
    def __init__(self, permission_codename=None):
        self.permission_codename = permission_codename
    
    def has_object_permission(self, request, view, obj):
        # Владелец всегда имеет доступ
        if hasattr(obj, 'owner') and obj.owner == request.user:
            return True
        
        # Проверяем конкретное разрешение
        if self.permission_codename:
            permission_checker = HasPermission(self.permission_codename)
            return permission_checker.has_object_permission(request, view, obj)
        
        return False