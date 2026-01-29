from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Кастомная модель пользователя"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField('Email', unique=True)
    first_name = models.CharField('Имя', max_length=150, blank=True)
    last_name = models.CharField('Фамилия', max_length=150, blank=True)
    patronymic = models.CharField('Отчество', max_length=150, blank=True)
    
    is_active = models.BooleanField('Активный', default=True)
    is_staff = models.BooleanField('Персонал', default=False)
    is_superuser = models.BooleanField('Суперпользователь', default=False)
    
    date_joined = models.DateTimeField('Дата регистрации', default=timezone.now)
    last_login = models.DateTimeField('Последний вход', null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        return f"{self.last_name} {self.first_name} {self.patronymic}".strip()
    
    def soft_delete(self):
        """Мягкое удаление пользователя"""
        self.is_active = False
        self.save()


class ResourceType(models.Model):
    """Тип ресурса (проект, документ и т.д.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Название', max_length=100, unique=True)
    code = models.CharField('Код', max_length=50, unique=True)
    description = models.TextField('Описание', blank=True)
    
    class Meta:
        verbose_name = 'Тип ресурса'
        verbose_name_plural = 'Типы ресурсов'
    
    def __str__(self):
        return self.name


class Permission(models.Model):
    """Разрешение (действие + тип ресурса)"""
    ACTION_CHOICES = [
        ('view', 'Просмотр'),
        ('create', 'Создание'),
        ('edit', 'Редактирование'),
        ('delete', 'Удаление'),
        ('manage', 'Управление'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codename = models.CharField('Кодовое имя', max_length=100, unique=True)
    name = models.CharField('Название', max_length=200)
    resource_type = models.ForeignKey(
        ResourceType,
        on_delete=models.CASCADE,
        verbose_name='Тип ресурса',
        related_name='permissions'
    )
    action = models.CharField('Действие', max_length=20, choices=ACTION_CHOICES)
    description = models.TextField('Описание', blank=True)
    
    class Meta:
        verbose_name = 'Разрешение'
        verbose_name_plural = 'Разрешения'
        unique_together = ['resource_type', 'action']
        ordering = ['resource_type', 'action']
    
    def __str__(self):
        return f"{self.name} ({self.resource_type.code})"
    
    def save(self, *args, **kwargs):
        if not self.codename:
            self.codename = f"{self.action}_{self.resource_type.code}"
        super().save(*args, **kwargs)


class Role(models.Model):
    """Роль пользователя"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Название', max_length=100, unique=True)
    code = models.CharField('Код', max_length=50, unique=True)
    description = models.TextField('Описание', blank=True)
    is_admin = models.BooleanField('Администратор', default=False)
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles',
        verbose_name='Разрешения'
    )
    
    class Meta:
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """Связь роли с разрешением (с условиями)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')
    conditions = models.JSONField('Условия', default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Разрешение роли'
        verbose_name_plural = 'Разрешения ролей'
        unique_together = ['role', 'permission']
    
    def __str__(self):
        return f"{self.role.name} - {self.permission.name}"


class UserRole(models.Model):
    """Связь пользователя с ролью"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField('Назначена', auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles',
        verbose_name='Назначил'
    )
    resource_scope = models.JSONField('Область действия', default=dict, blank=True)
    
    class Meta:
        verbose_name = 'Роль пользователя'
        verbose_name_plural = 'Роли пользователей'
        unique_together = ['user', 'role']
    
    def __str__(self):
        return f"{self.user.email} - {self.role.name}"


class Resource(models.Model):
    """Ресурс (проект, документ и т.д.)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    resource_type = models.ForeignKey(
        ResourceType,
        on_delete=models.CASCADE,
        related_name='resources',
        verbose_name='Тип ресурса'
    )
    name = models.CharField('Название', max_length=200)
    description = models.TextField('Описание', blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_resources',
        verbose_name='Владелец'
    )
    metadata = models.JSONField('Метаданные', default=dict, blank=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    is_active = models.BooleanField('Активный', default=True)
    
    class Meta:
        verbose_name = 'Ресурс'
        verbose_name_plural = 'Ресурсы'
        indexes = [
            models.Index(fields=['resource_type', 'owner']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name


class ResourceAccess(models.Model):
    """Прямой доступ к ресурсу"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='resource_accesses')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='accesses')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='resource_accesses')
    granted_at = models.DateTimeField('Предоставлен', auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_accesses',
        verbose_name='Предоставил'
    )
    conditions = models.JSONField('Условия', default=dict, blank=True)
    expires_at = models.DateTimeField('Истекает', null=True, blank=True)
    
    class Meta:
        verbose_name = 'Доступ к ресурсу'
        verbose_name_plural = 'Доступы к ресурсам'
        unique_together = ['user', 'resource', 'permission']
    
    def __str__(self):
        return f"{self.user.email} - {self.resource.name} - {self.permission.name}"
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class AuditLog(models.Model):
    """Лог действий пользователей"""
    ACTION_CHOICES = [
        ('login', 'Вход'),
        ('logout', 'Выход'),
        ('create', 'Создание'),
        ('update', 'Обновление'),
        ('delete', 'Удаление'),
        ('access_granted', 'Доступ предоставлен'),
        ('access_revoked', 'Доступ отозван'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name='Пользователь'
    )
    action = models.CharField('Действие', max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField('Тип ресурса', max_length=100, blank=True)
    resource_id = models.CharField('ID ресурса', max_length=100, blank=True)
    details = models.JSONField('Детали', default=dict, blank=True)
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)
    timestamp = models.DateTimeField('Время', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Лог действий'
        verbose_name_plural = 'Логи действий'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user.email if self.user else 'Anonymous'} - {self.action} - {self.timestamp}"