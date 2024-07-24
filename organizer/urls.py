# attendee/urls.py
from django.urls import path
from organizer import views


urlpatterns = [
    path('home/', views.home, name='organizer_dashboard'),
    path('add_event/', views.add_event, name='add_event'),
    path('see_events/', views.events_list, name='events_list'),
    path('event_edit/<int:event_id>/', views.edit_event, name='edit_event'),
    path('see_payments/', views.payment_details, name='see_payments'),
    path('share_events/', views.event_share, name='share_events'),
    path('profile/', views.profile, name='profile'),
    path('delete_event/<int:event_id>/', views.delete_event, name='delete_event'),
    path('event_details/<int:event_id>/', views.public_event_view, name="public_event_view")
]
