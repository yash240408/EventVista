# authentication/urls.py
from django.urls import path, include
from authuser import views

urlpatterns = [
    path('register/', views.normal_signup, name='register'),
    path('login/', views.normal_login, name='login'),

    path('google/login/', views.google_login, name='google_login'),
    path('google/login/callback/', views.google_callback, name='google_callback'),

    path('logout/', views.user_logout, name='logout'),

    path('profile/', views.profile, name='profile'),
    path('socialRole/', views.socialRole, name='socialRole'),

    path('attendee/', include('attendee.urls')),
]
