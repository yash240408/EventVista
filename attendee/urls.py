# attendee/urls.py
from django.urls import path
from attendee import views

urlpatterns = [
    path('home/', views.home, name='attendee_dashboard'),
    path('create_checkout_session/', views.create_checkout_session, name='create_checkout_session'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-error/', views.payment_cancel, name='payment_error'),
    path('payment-cancel/', views.payment_cancel, name='payment_cancel'),
]
