from django.urls import path
from . import views

urlpatterns = [
    # Бизнес-эндпоинты
    path('projects/', views.ProjectListView.as_view(), name='project-list'),
    path('projects/<uuid:project_id>/', views.ProjectDetailView.as_view(), name='project-detail'),
    path('projects/create/', views.CreateProjectView.as_view(), name='project-create'),
    
    path('documents/', views.DocumentListView.as_view(), name='document-list'),
    path('documents/<uuid:document_id>/download/', views.DocumentDownloadView.as_view(), name='document-download'),
    
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Демонстрационные эндпоинты
    path('demo/access/', views.AccessDeniedDemoView.as_view(), name='access-demo'),
]