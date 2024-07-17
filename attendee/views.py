# attendee/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser  
from authuser.models import User

@login_required
def home(request):
    if request.user.is_authenticated:
        # Further debugging of user attributes
        fullname = request.user.fullname if hasattr(request.user, 'fullname') else None
        role = request.user.role if hasattr(request.user, 'role') else None
        
        context = {
            'fullname': fullname,
            'role': role
        }
        return render(request, "dashboard.html", context)
    else:
        return redirect('login', {'error': 'Please Login First'})