from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from authuser.views import *
urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('authuser.urls')),
    path('attendee/', include('attendee.urls')),
    path('organizer/', include('organizer.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)