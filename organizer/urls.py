# attendee/urls.py
from django.urls import path
from attendee import views


urlpatterns = [
    path('home/', views.home, name='organizer_dashboard'),
    # path('login/', views.user_login, name='login'),
    # path('logout/', views.user_logout, name='logout'),
    # path('profile/', views.profile, name='profile'),
]
