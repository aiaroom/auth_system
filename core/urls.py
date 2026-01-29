from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, UserProfileView,
    RoleViewSet, PermissionViewSet, UserRoleViewSet,
    ResourceTypeViewSet, ResourceViewSet, ResourceAccessViewSet,
    InitializeSystemView
)

router = DefaultRouter()
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'user-roles', UserRoleViewSet, basename='user-role')
router.register(r'resource-types', ResourceTypeViewSet, basename='resource-type')
router.register(r'resources', ResourceViewSet, basename='resource')
router.register(r'resource-access', ResourceAccessViewSet, basename='resource-access')

urlpatterns = [
    # Аутентификация
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Профиль пользователя
    path('profile/', UserProfileView.as_view(), name='profile'),
    
    # Системные эндпоинты
    path('system/initialize/', InitializeSystemView.as_view(), name='initialize-system'),
    
    # API маршруты
    path('', include(router.urls)),
]