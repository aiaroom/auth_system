#!/usr/bin/env python
"""
Скрипт для создания тестовых данных
"""

import os
import sys
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from django.contrib.auth import get_user_model
from core.models import (
    Role, Permission, UserRole, ResourceType,
    Resource, ResourceAccess
)
from core.utils import create_default_permissions
from django.utils import timezone
from datetime import timedelta
import uuid

User = get_user_model()

def create_test_data():
    print("Создание тестовых данных...")
    
    # 1. Создаем стандартные разрешения
    print("Создание стандартных разрешений...")
    create_default_permissions()
    
    # 2. Создаем дополнительные разрешения для документов
    print("Создание дополнительных разрешений...")
    document_type = ResourceType.objects.get(code='document')
    
    additional_perms = [
        ('download_document', 'Скачивание документов', 'download'),
        ('upload_document', 'Загрузка документов', 'upload'),
    ]
    
    for codename, name, action in additional_perms:
        Permission.objects.get_or_create(
            codename=codename,
            defaults={
                'name': name,
                'resource_type': document_type,
                'action': action,
                'description': f'Разрешение на {name.lower()}'
            }
        )
    
    # 3. Создаем стандартные роли
    print("Создание ролей...")
    
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
    
    # Роль просмотра
    viewer_role, created = Role.objects.get_or_create(
        code='viewer',
        defaults={
            'name': 'Наблюдатель',
            'description': 'Только просмотр проектов и документов',
            'is_admin': False
        }
    )
    
    # 4. Назначаем разрешения ролям
    print("Назначение разрешений ролям...")
    
    # Получаем типы ресурсов
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
    
    # Разрешения для наблюдателя
    viewer_permissions = Permission.objects.filter(
        resource_type__in=[project_type, document_type],
        action='view'
    )
    viewer_role.permissions.set(viewer_permissions)
    
    # Разрешения для администратора
    all_permissions = Permission.objects.all()
    admin_role.permissions.set(all_permissions)
    
    # 5. Создаем тестовых пользователей
    print("Создание тестовых пользователей...")
    
    test_users = [
        {
            'email': 'admin@example.com',
            'password': 'Admin123!',
            'first_name': 'Алексей',
            'last_name': 'Администраторов',
            'role': admin_role
        },
        {
            'email': 'manager@example.com',
            'password': 'Manager123!',
            'first_name': 'Мария',
            'last_name': 'Менеджерова',
            'role': manager_role
        },
        {
            'email': 'user1@example.com',
            'password': 'User123!',
            'first_name': 'Иван',
            'last_name': 'Иванов',
            'role': user_role
        },
        {
            'email': 'user2@example.com',
            'password': 'User123!',
            'first_name': 'Петр',
            'last_name': 'Петров',
            'role': user_role
        },
        {
            'email': 'viewer@example.com',
            'password': 'Viewer123!',
            'first_name': 'Светлана',
            'last_name': 'Сидорова',
            'role': viewer_role
        },
    ]
    
    created_users = []
    for user_data in test_users:
        email = user_data.pop('email')
        password = user_data.pop('password')
        role = user_data.pop('role')
        
        # Создаем или получаем пользователя
        user, created = User.objects.get_or_create(
            email=email,
            defaults=user_data
        )
        
        if created:
            user.set_password(password)
            user.save()
        
        # Назначаем роль
        UserRole.objects.get_or_create(
            user=user,
            role=role,
            defaults={'assigned_by': User.objects.filter(is_superuser=True).first()}
        )
        
        created_users.append(user)
        print(f"  Создан пользователь: {email} ({role.name})")
    
    # 6. Создаем тестовые ресурсы (упрощенная версия без download_document)
    print("Создание тестовых ресурсов...")
    
    admin_user = User.objects.get(email='admin@example.com')
    manager_user = User.objects.get(email='manager@example.com')
    user1 = User.objects.get(email='user1@example.com')
    
    # Проекты
    projects = [
        {
            'name': 'Разработка CRM системы',
            'description': 'Создание системы управления клиентами',
            'resource_type': project_type,
            'owner': admin_user,
            'metadata': {'budget': 1500000, 'status': 'active', 'team_size': 8}
        },
        {
            'name': 'Модернизация сайта',
            'description': 'Обновление дизайна и функционала корпоративного сайта',
            'resource_type': project_type,
            'owner': manager_user,
            'metadata': {'budget': 800000, 'status': 'planning', 'team_size': 5}
        },
        {
            'name': 'Внедрение CI/CD',
            'description': 'Настройка процессов непрерывной интеграции и доставки',
            'resource_type': project_type,
            'owner': user1,
            'metadata': {'budget': 500000, 'status': 'in_progress', 'team_size': 3}
        },
    ]
    
    created_projects = []
    for project_data in projects:
        project, created = Resource.objects.get_or_create(
            name=project_data['name'],
            resource_type=project_data['resource_type'],
            defaults=project_data
        )
        created_projects.append(project)
        print(f"  Создан проект: {project.name}")
    
    # Документы
    documents = [
        {
            'name': 'Техническое задание CRM.pdf',
            'description': 'Детальное описание требований к CRM системе',
            'resource_type': document_type,
            'owner': admin_user,
            'metadata': {'file_type': 'pdf', 'size_mb': 2.5, 'pages': 45}
        },
        {
            'name': 'Презентация проекта сайта.pptx',
            'description': 'Презентация для руководства',
            'resource_type': document_type,
            'owner': manager_user,
            'metadata': {'file_type': 'pptx', 'size_mb': 8.2, 'slides': 32}
        },
        {
            'name': 'Отчет по анализу CI/CD.xlsx',
            'description': 'Результаты анализа текущих процессов',
            'resource_type': document_type,
            'owner': user1,
            'metadata': {'file_type': 'xlsx', 'size_mb': 1.8, 'sheets': 5}
        },
    ]
    
    created_documents = []
    for doc_data in documents:
        document, created = Resource.objects.get_or_create(
            name=doc_data['name'],
            resource_type=doc_data['resource_type'],
            defaults=doc_data
        )
        created_documents.append(document)
        print(f"  Создан документ: {document.name}")
    
    # 7. Настраиваем доступ к ресурсам (без download_document)
    print("Настройка доступа к ресурсам...")
    
    # Получаем разрешения
    view_project_perm = Permission.objects.get(codename='view_project')
    edit_project_perm = Permission.objects.get(codename='edit_project')
    view_document_perm = Permission.objects.get(codename='view_document')
    
    # Даем пользователю 2 доступ к проекту менеджера
    user2 = User.objects.get(email='user2@example.com')
    viewer_user = User.objects.get(email='viewer@example.com')
    
    # Доступ к просмотру проекта
    ResourceAccess.objects.get_or_create(
        user=user2,
        resource=created_projects[1],  # Проект менеджера
        permission=view_project_perm,
        defaults={
            'granted_by': admin_user,
            'expires_at': timezone.now() + timedelta(days=30)
        }
    )
    
    # Доступ к просмотру документа
    ResourceAccess.objects.get_or_create(
        user=viewer_user,
        resource=created_documents[0],  # Документ администратора
        permission=view_document_perm,
        defaults={
            'granted_by': admin_user,
            'expires_at': timezone.now() + timedelta(days=7)
        }
    )
    
    print("\nТестовые данные успешно созданы!")
    print("\nДоступы для тестирования:")
    print("=" * 50)
    print("1. Администратор:")
    print("   Email: admin@example.com")
    print("   Пароль: Admin123!")
    print("   Права: Полный доступ ко всему")
    print()
    print("2. Менеджер:")
    print("   Email: manager@example.com")
    print("   Пароль: Manager123!")
    print("   Права: Управление проектами и документами")
    print()
    print("3. Пользователь 1:")
    print("   Email: user1@example.com")
    print("   Пароль: User123!")
    print("   Права: Просмотр и создание проектов/документов")
    print()
    print("4. Пользователь 2:")
    print("   Email: user2@example.com")
    print("   Пароль: User123!")
    print("   Права: Пользователь + доступ к проекту менеджера")
    print()
    print("5. Наблюдатель:")
    print("   Email: viewer@example.com")
    print("   Пароль: Viewer123!")
    print("   Права: Только просмотр")
    print("=" * 50)
if __name__ == '__main__':
    create_test_data()