# organizer/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

@login_required
def home(request):
    if request.user.is_authenticated:
        fullname = request.user.fullname if hasattr(request.user, 'fullname') else None
        role = request.user.role if hasattr(request.user, 'role') else None        
        context = {
            'fullname': fullname,
            'role': role
        }
        return render(request, "dashboard.html", context)
    else:
        return redirect('login', {'error': 'Please Login First'})