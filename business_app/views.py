from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, BasePermission
from django.utils import timezone
import uuid

from core.utils import log_action


# Простые кастомные классы разрешений
class CanViewProjects(BasePermission):
    """Может ли пользователь просматривать проекты"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.is_active


class CanCreateProjects(BasePermission):
    """Может ли пользователь создавать проекты"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if not request.user.is_active:
            return False
        
        # Проверяем, есть ли у пользователя роль admin или manager
        from core.models import UserRole
        user_roles = UserRole.objects.filter(user=request.user)
        
        for user_role in user_roles:
            if user_role.role.code in ['admin', 'manager']:
                return True
        
        return False


class CanViewDocuments(BasePermission):
    """Может ли пользователь просматривать документы"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.is_active


class ProjectListView(APIView):
    """Список проектов (моковые данные)"""
    permission_classes = [CanViewProjects]
    
    def get(self, request):
        # Моковые проекты для демонстрации
        mock_projects = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Проект Альфа',
                'description': 'Разработка новой системы управления',
                'status': 'active',
                'created_at': '2024-01-15T10:00:00Z',
                'owner': request.user.email
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Проект Бета',
                'description': 'Модернизация инфраструктуры',
                'status': 'planning',
                'created_at': '2024-02-01T14:30:00Z',
                'owner': request.user.email
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Проект Гамма',
                'description': 'Внедрение системы безопасности',
                'status': 'completed',
                'created_at': '2023-12-10T09:15:00Z',
                'owner': request.user.email
            },
        ]
        
        # Логируем доступ
        log_action(
            user=request.user,
            action='view',
            resource_type='project',
            details={'action': 'list_projects'}
        )
        
        return Response({
            'message': 'Список проектов',
            'mock_projects': mock_projects,
            'total': len(mock_projects)
        })


class ProjectDetailView(APIView):
    """Детали проекта (моковые данные)"""
    permission_classes = [CanViewProjects]
    
    def get(self, request, project_id):
        # Моковые данные для демонстрации
        mock_projects = {
            '550e8400-e29b-41d4-a716-446655440000': {
                'id': '550e8400-e29b-41d4-a716-446655440000',
                'name': 'Проект Альфа',
                'description': 'Разработка новой системы управления',
                'status': 'active',
                'owner': request.user.email,
                'created_at': '2024-01-15T10:00:00Z',
                'team_members': [
                    {'name': 'Иван Иванов', 'role': 'Team Lead'},
                    {'name': 'Петр Петров', 'role': 'Backend Developer'},
                    {'name': 'Сидор Сидоров', 'role': 'Frontend Developer'},
                ],
                'tasks_completed': 42,
                'tasks_total': 100,
                'budget': '1,200,000 руб.',
                'deadline': '2024-06-30'
            }
        }
        
        if project_id in mock_projects:
            # Логируем доступ к моковому проекту
            log_action(
                user=request.user,
                action='view',
                resource_type='project',
                resource_id=project_id,
                details={'mock_data': True}
            )
            
            return Response({
                'message': 'Детали проекта (моковые данные)',
                'project': mock_projects[project_id],
                'note': 'Это демонстрационные данные'
            })
        
        return Response(
            {'error': 'Проект не найден'},
            status=status.HTTP_404_NOT_FOUND
        )


class DocumentListView(APIView):
    """Список документов (моковые данные)"""
    permission_classes = [CanViewDocuments]
    
    def get(self, request):
        # Моковые документы
        mock_documents = [
            {
                'id': str(uuid.uuid4()),
                'name': 'Техническое задание.pdf',
                'type': 'pdf',
                'size': '2.4 MB',
                'uploaded_at': '2024-01-20T11:30:00Z',
                'owner': request.user.email
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Презентация проекта.pptx',
                'type': 'pptx',
                'size': '5.1 MB',
                'uploaded_at': '2024-01-18T15:45:00Z',
                'owner': request.user.email
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Бюджет проекта.xlsx',
                'type': 'xlsx',
                'size': '1.2 MB',
                'uploaded_at': '2024-01-17T09:20:00Z',
                'owner': request.user.email
            },
        ]
        
        # Логируем доступ
        log_action(
            user=request.user,
            action='view',
            resource_type='document',
            details={'action': 'list_documents'}
        )
        
        return Response({
            'message': 'Список документов',
            'mock_documents': mock_documents,
            'total': len(mock_documents)
        })


class DocumentDownloadView(APIView):
    """Скачивание документа (моковые данные)"""
    permission_classes = [CanViewDocuments]
    
    def get(self, request, document_id):
        # Моковые данные для демонстрации
        mock_documents = {
            '550e8400-e29b-41d4-a716-446655440001': {
                'id': '550e8400-e29b-41d4-a716-446655440001',
                'name': 'Техническое задание.pdf',
                'content': 'Моковое содержимое PDF файла',
                'mime_type': 'application/pdf',
                'size': 2516582  # 2.4 MB в байтах
            }
        }
        
        if document_id in mock_documents:
            # Логируем скачивание
            log_action(
                user=request.user,
                action='download',
                resource_type='document',
                resource_id=document_id,
                details={
                    'file_name': mock_documents[document_id]['name'],
                    'file_size': mock_documents[document_id]['size']
                }
            )
            
            return Response({
                'message': 'Документ готов к скачиванию',
                'document': mock_documents[document_id],
                'download_url': f'/api/documents/{document_id}/download/file/',
                'note': 'Это демонстрационные данные. В реальном приложении здесь был бы файл.'
            })
        
        return Response(
            {'error': 'Документ не найден'},
            status=status.HTTP_404_NOT_FOUND
        )


class DashboardView(APIView):
    """Панель управления (моковые данные)"""
    permission_classes = [CanViewProjects]
    
    def get(self, request):
        # Проверяем разные уровни доступа
        from core.models import UserRole
        
        user_roles = UserRole.objects.filter(user=request.user)
        role_names = [ur.role.name for ur in user_roles]
        
        # Простая проверка прав на основе ролей
        has_project_view = False
        has_document_view = False
        has_user_manage = False
        
        for user_role in user_roles:
            role_code = user_role.role.code
            if role_code in ['admin', 'manager', 'user', 'viewer']:
                has_project_view = True
            if role_code in ['admin', 'manager', 'user']:
                has_document_view = True
            if role_code == 'admin':
                has_user_manage = True
        
        # Логируем доступ к панели
        log_action(
            user=request.user,
            action='view',
            resource_type='dashboard'
        )
        
        return Response({
            'message': 'Панель управления',
            'user': {
                'email': request.user.email,
                'full_name': request.user.get_full_name(),
                'roles': role_names
            },
            'permissions': {
                'view_projects': has_project_view,
                'view_documents': has_document_view,
                'manage_users': has_user_manage,
            },
            'stats': {
                'total_projects': 15,
                'active_projects': 8,
                'total_documents': 127,
                'storage_used': '2.3 GB'
            },
            'recent_activity': [
                {
                    'action': 'Создан проект',
                    'project': 'Проект Альфа',
                    'time': '2 часа назад'
                },
                {
                    'action': 'Загружен документ',
                    'document': 'Техническое задание.pdf',
                    'time': 'Вчера, 14:30'
                },
                {
                    'action': 'Обновлен профиль',
                    'details': 'Изменена контактная информация',
                    'time': '3 дня назад'
                }
            ]
        })


class CreateProjectView(APIView):
    """Создание нового проекта"""
    permission_classes = [CanCreateProjects]
    
    def post(self, request):
        project_data = {
            'id': str(uuid.uuid4()),
            'name': request.data.get('name', 'Новый проект'),
            'description': request.data.get('description', ''),
            'owner': request.user.email,
            'created_at': timezone.now().isoformat(),
            'status': 'draft'
        }
        
        # Логируем создание
        log_action(
            user=request.user,
            action='create',
            resource_type='project',
            resource_id=project_data['id'],
            details={'project_name': project_data['name']}
        )
        
        return Response({
            'message': 'Проект создан успешно',
            'project': project_data,
            'note': 'В реальном приложении проект был бы сохранен в базу данных'
        }, status=status.HTTP_201_CREATED)


class AccessDeniedDemoView(APIView):
    """Демонстрация ошибок доступа"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        demo_type = request.query_params.get('type', '401')
        
        if demo_type == '401':
            return Response(
                {
                    'error': 'Authentication credentials were not provided.',
                    'code': 'not_authenticated',
                    'message': 'Требуется аутентификация'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        elif demo_type == '403':
            return Response(
                {
                    'error': 'You do not have permission to perform this action.',
                    'code': 'permission_denied',
                    'message': 'Доступ запрещен'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        else:
            return Response({
                'message': 'Демонстрация ошибок доступа',
                'available_demos': {
                    '401': '/api/demo/access/?type=401 - Ошибка аутентификации',
                    '403': '/api/demo/access/?type=403 - Ошибка авторизации'
                }
            })