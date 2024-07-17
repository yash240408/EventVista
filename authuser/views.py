# authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from authuser.models import User
from django.core.files.base import ContentFile
from django.urls import reverse
from django.conf import settings
import requests

@csrf_exempt
def normal_signup(request):
    if request.method == 'POST':
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        phone = request.POST.get("phone")
        role = request.POST.get("role")
        profile_picture = request.FILES.get('profile_picture')

        if not all([name, email, password, phone, role, profile_picture]):
            return render(request, 'signup.html', {'error': 'All fields are required.'})

        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email already exists.'})

        if User.objects.filter(phone=phone).exists():
            return render(request, 'signup.html', {'error': 'Phone Number already exists.'})

        new_user = User(
            fullname=name,
            email=email,
            phone=phone,
            role=role,
            profile_picture=profile_picture
        )
        new_user.set_password(password)
        new_user.save()

        return redirect('login')

    return render(request, 'signup.html')


@csrf_exempt
def normal_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            if user.role == 'attendee':
                login(request, user)  # Ensure the user is logged in
                return redirect('attendee_dashboard')
            elif user.role == 'organizer':
                login(request, user)  # Ensure the user is logged in
                return redirect('organizer_dashboard')
            elif user.role == 'administrator':
                login(request, user)  # Ensure the user is logged in
                return redirect('admin_dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid email or password.'})

    return render(request, 'login.html')


def user_logout(request):
    logout(request)
    return redirect('login')


@login_required
def profile(request):
    user = request.user

    user_details = {
        'fullname': user.fullname,
        'email': user.email,
        'phone': user.phone,
        'role': user.role,
        'profile_picture': user.profile_picture.url if user.profile_picture else None
    }

    return render(request, 'profile.html', {'user_details': user_details})



def socialRole(request):
    role = request.POST.get("role")
    phone = request.POST.get("phone")

    return render(request, "socialadd.html")


# Google Handling Starts

def google_login(request):
    client_id = settings.GOOGLE_CLIENT_ID
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth/oauthchooseaccount?"
        f"client_id={client_id}&redirect_uri=http://127.0.0.1:8000/accounts/google/login/callback/&scope=profile%20email&response_type=code"        
    )
    return redirect(auth_url)

"""
def google_callback(request):
    code = request.GET.get('code')
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
    access_token = token_json.get('access_token')

    user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    user_info_params = {'access_token': access_token}
    user_info_response = requests.get(user_info_url, params=user_info_params)
    user_info = user_info_response.json()

    # Extract user information
    email = user_info['email']
    first_name = user_info['given_name']
    last_name = user_info['family_name']

    # Create or update the user
    user, created = User.objects.get_or_create(email=email, defaults={'fullname': first_name+" "+last_name})
    if created:
        user.set_unusable_password()
        user.save()

    login(request, user)

    return redirect('socialRole')  
"""

def google_callback(request):
    code = request.GET.get('code')
    client_id = settings.GOOGLE_CLIENT_ID
    client_secret = settings.GOOGLE_CLIENT_SECRET
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }
    
    try:
        token_response = requests.post(token_url, data=token_data)
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
        user_info_params = {'access_token': access_token}
        user_info_response = requests.get(user_info_url, params=user_info_params)
        user_info = user_info_response.json()

        
        email = user_info.get('email', '')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        picture = user_info.get('picture', '')
        response = requests.get(picture)

        user, created = User.objects.get_or_create(email=email, defaults={'fullname': first_name+" "+last_name})
        if created:
            user.profile_picture.save(f'{email}_profile.jpg', ContentFile(response.content), save=True)
            user.set_unusable_password()
            user.save()
        
        login(request, user)
        
        return redirect('socialRole')  
    
    except requests.exceptions.RequestException as e:
        print(f"RequestException: {e}")
        return redirect('/')  
    
    except KeyError as e:
        print(f"KeyError: {e}")
        return redirect('/') 