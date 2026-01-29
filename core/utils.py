from .models import AuditLog


def log_action(user, action, resource_type='', resource_id='', details=None, 
               request=None):
    """
    Логирует действие пользователя
    """
    audit_log = AuditLog(
        user=user,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {}
    )
    
    if request:
        audit_log.ip_address = get_client_ip(request)
        audit_log.user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    audit_log.save()
    return audit_log


def get_client_ip(request):
    """
    Получает IP адрес клиента из запроса
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_resource_access(user, resource, permission_codename):
    """
    Проверяет доступ пользователя к ресурсу
    """
    from .permissions import HasPermission
    
    permission_checker = HasPermission(permission_codename)
    return permission_checker.has_object_permission(None, None, resource)


def soft_delete_user(user):
    """
    Мягкое удаление пользователя
    """
    user.is_active = False
    user.save()
    


def create_default_permissions():
    """
    Создает стандартные разрешения
    """
    from .models import ResourceType, Permission
    
    # Типы ресурсов
    resource_types = [
        ('project', 'Проект'),
        ('document', 'Документ'),
        ('user', 'Пользователь'),
        ('role', 'Роль'),
        ('permission', 'Разрешение'),
    ]
    
    actions = ['view', 'create', 'edit', 'delete', 'manage']
    
    for code, name in resource_types:
        resource_type, created = ResourceType.objects.get_or_create(
            code=code,
            defaults={'name': name}
        )
        
        for action in actions:
            codename = f"{action}_{code}"
            name_ru = {
                'view': f'Просмотр {name.lower()}ов',
                'create': f'Создание {name.lower()}ов',
                'edit': f'Редактирование {name.lower()}ов',
                'delete': f'Удаление {name.lower()}ов',
                'manage': f'Управление {name.lower()}ами',
            }[action]
            
            Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name_ru,
                    'resource_type': resource_type,
                    'action': action,
                    'description': f'Разрешение на {action} {name.lower()}ов'
                }
            )