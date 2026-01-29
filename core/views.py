from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated as DRFIsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError

from .models import (
    User, Role, Permission, UserRole, ResourceType,
    Resource, ResourceAccess
)
from .serializers import (
    RegisterSerializer, LoginSerializer, UserSerializer,
    UserUpdateSerializer, RoleSerializer, PermissionSerializer,
    UserRoleSerializer, ResourceTypeSerializer, ResourceSerializer,
    ResourceAccessSerializer
)
from .permissions import IsAuthenticated, HasPermission, IsAdmin, IsOwnerOrHasPermission
from .utils import log_action, soft_delete_user, create_default_permissions


class RegisterView(generics.CreateAPIView):
    """Регистрация пользователя"""
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Создаем токены
        refresh = RefreshToken.for_user(user)
        
        # Логируем регистрацию
        log_action(
            user=user,
            action='create',
            resource_type='user',
            resource_id=str(user.id),
            details={'action': 'registration'},
            request=request
        )
        
        return Response({
            'message': 'Регистрация успешна',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Вход в систему"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Создаем токены
        refresh = RefreshToken.for_user(user)
        
        # Обновляем последний вход
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        
        # Логируем вход
        log_action(
            user=user,
            action='login',
            request=request
        )
        
        return Response({
            'message': 'Вход выполнен успешно',
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })


class LogoutView(APIView):
    """Выход из системы"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist() 
            else:
                pass
            
            log_action(
                user=request.user,
                action='logout',
                request=request
            )
            
            return Response({'message': 'Выход выполнен успешно'})
        except TokenError as e:
            return Response(
                {'error': f'Ошибка токена: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class UserProfileView(generics.RetrieveUpdateDestroyAPIView):
    """Профиль пользователя"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Мягкое удаление
        soft_delete_user(user)
        
        # Логируем удаление
        log_action(
            user=user,
            action='delete',
            resource_type='user',
            resource_id=str(user.id),
            details={'action': 'soft_delete'},
            request=request
        )
        
        # Выход из системы
        try:
                refresh_token = request.data.get('refresh')
                if refresh_token:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
        except:
                pass 
                    
        return Response(
            {'message': 'Аккаунт успешно удален'},
            status=status.HTTP_200_OK
        )


# Административные представления
class RoleViewSet(viewsets.ModelViewSet):
    """Управление ролями (только для администраторов)"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_fields = ['is_admin']
    search_fields = ['name', 'code', 'description']


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр разрешений (только для администраторов)"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_fields = ['resource_type', 'action']
    search_fields = ['codename', 'name']


class UserRoleViewSet(viewsets.ModelViewSet):
    """Управление ролями пользователей (только для администраторов)"""
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        role_id = self.request.query_params.get('role_id')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if role_id:
            queryset = queryset.filter(role_id=role_id)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(assigned_by=self.request.user)
        
        # Логируем назначение роли
        log_action(
            user=self.request.user,
            action='access_granted',
            resource_type='role',
            resource_id=str(serializer.instance.role_id),
            details={
                'assigned_to': str(serializer.instance.user_id),
                'role': serializer.instance.role.name
            }
        )


class ResourceTypeViewSet(viewsets.ModelViewSet):
    """Управление типами ресурсов (только для администраторов)"""
    queryset = ResourceType.objects.all()
    serializer_class = ResourceTypeSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class ResourceViewSet(viewsets.ModelViewSet):
    """Управление ресурсами"""
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        elif self.action == 'create':
            permission_classes = [IsAuthenticated, HasPermission('create_project')]
        else:
            permission_classes = [IsAuthenticated, IsOwnerOrHasPermission('edit_project')]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        user = self.request.user
        
        # Администраторы видят все
        if user.is_superuser or user.user_roles.filter(role__is_admin=True).exists():
            return Resource.objects.all()
        
        # Владельцы видят свои ресурсы
        queryset = Resource.objects.filter(owner=user)
        
        # Пользователи видят ресурсы, к которым у них есть доступ
        user_access = ResourceAccess.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).values_list('resource_id', flat=True)
        
        if user_access:
            queryset = queryset | Resource.objects.filter(id__in=user_access)
        
        return queryset.distinct()


class ResourceAccessViewSet(viewsets.ModelViewSet):
    """Управление доступом к ресурсам"""
    queryset = ResourceAccess.objects.all()
    serializer_class = ResourceAccessSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        resource_id = self.request.query_params.get('resource_id')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)
        
        # Логируем предоставление доступа
        log_action(
            user=self.request.user,
            action='access_granted',
            resource_type='resource_access',
            resource_id=str(serializer.instance.id),
            details={
                'user': str(serializer.instance.user_id),
                'resource': str(serializer.instance.resource_id),
                'permission': serializer.instance.permission.codename
            }
        )


class InitializeSystemView(APIView):
    """Инициализация системы (создание стандартных данных)"""
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def post(self, request):
        try:
            # Создаем стандартные разрешения
            create_default_permissions()
            
            # Создаем стандартные роли
            from .models import Role, Permission, ResourceType
            
            # Роль администратора
            admin_role, created = Role.objects.get_or_create(
                code='admin',
                defaults={
                    'name': 'Администратор',
                    'description': 'Полный доступ ко всем функциям системы',
                    'is_admin': True
                }
            )
            
            # Роль менеджера
            manager_role, created = Role.objects.get_or_create(
                code='manager',
                defaults={
                    'name': 'Менеджер',
                    'description': 'Управление проектами и документами',
                    'is_admin': False
                }
            )
            
            # Роль пользователя
            user_role, created = Role.objects.get_or_create(
                code='user',
                defaults={
                    'name': 'Пользователь',
                    'description': 'Базовый пользователь',
                    'is_admin': False
                }
            )
            
            # Назначаем разрешения ролям
            project_type = ResourceType.objects.get(code='project')
            document_type = ResourceType.objects.get(code='document')
            
            # Разрешения для менеджера
            manager_permissions = Permission.objects.filter(
                resource_type__in=[project_type, document_type]
            ).exclude(action='manage')
            
            manager_role.permissions.set(manager_permissions)
            
            # Разрешения для пользователя
            user_permissions = Permission.objects.filter(
                resource_type__in=[project_type, document_type],
                action__in=['view', 'create']
            )
            
            user_role.permissions.set(user_permissions)
            
            # Назначаем администратору все разрешения
            all_permissions = Permission.objects.all()
            admin_role.permissions.set(all_permissions)
            
            return Response({
                'message': 'Система инициализирована успешно',
                'created_roles': [
                    admin_role.name,
                    manager_role.name,
                    user_role.name
                ]
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )