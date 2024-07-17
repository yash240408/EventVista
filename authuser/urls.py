# authentication/urls.py
from django.urls import path, include
from authuser import views

urlpatterns = [
    path('register/', views.normal_signup, name='register'),
    path('login/', views.normal_login, name='login'),

    path('google/login/', views.google_login, name='google_login'),
    path('google/login/callback/', views.google_callback, name='google_callback'),

    path('github/login/', views.github_login, name='github_login'),
    path('github/callback/', views.github_callback, name='github_callback'),

    path('logout/', views.user_logout, name='logout'),

    path('profile/', views.profile, name='profile'),
    path('additional_info/', views.additional_info, name='additional_info'),

    path('attendee/', include('attendee.urls')),
    path('organizer/', include('organizer.urls')),
]
