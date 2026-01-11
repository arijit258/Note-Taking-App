from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Notes CRUD
    path('notes/new/', views.note_create, name='note_create'),
    path('notes/<int:pk>/', views.note_detail, name='note_detail'),
    path('notes/<int:pk>/edit/', views.note_edit, name='note_edit'),
    path('notes/<int:pk>/delete/', views.note_delete, name='note_delete'),
    
    # Sharing
    path('notes/<int:pk>/share/', views.note_share, name='note_share'),
    path('notes/<int:pk>/unshare/<int:user_id>/', views.note_unshare, name='note_unshare'),
    
    # User search
    path('api/users/search/', views.user_search, name='user_search'),
    
    # Versioning
    path('notes/<int:pk>/restore/<int:version_id>/', views.note_restore_version, name='note_restore_version'),
]
