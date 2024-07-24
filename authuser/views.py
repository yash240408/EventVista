# authentication/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from authuser.models import User
from django.core.files.base import ContentFile
from django.urls import reverse
from django.conf import settings
import requests
from organizer.models import Event, Ticket



def index(request):
    events = Event.objects.all()
    event_details = []

    for event in events:
        tickets = Ticket.objects.filter(event=event)
        event_details.append({
            'event': event,
            'tickets': tickets
        })
    return render(request, 'index.html', {'event_details': event_details})


@csrf_exempt
def normal_signup(request):
    try:
        if request.user.is_authenticated:
            return redirect_role_based(request.user)

        if request.method == 'POST':
            name = request.POST.get("name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            phone = request.POST.get("phone")
            role = request.POST.get("role")
            profile_picture = request.FILES.get('profile_picture')
            gender = request.POST.get('gender')
            pincode = request.POST.get('pincode')
            age = request.POST.get('age')

            if not all([name, email, password, phone, role, profile_picture, gender, age, pincode]):
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
                profile_picture=profile_picture,
                gender=gender,
                age=age,
                pincode=pincode

            )
            new_user.set_password(password)
            new_user.save()

            login(request, new_user)
            return redirect_role_based(new_user)

        else:
            return render(request, "signup.html")
    
    except Exception as e:
        print("Normal Signup Exception:", e)
        return render(request, 'signup.html', {'error': 'An error occurred during signup.'})
    

@csrf_exempt
def normal_login(request):
    if request.user.is_authenticated:
        return redirect_role_based(request.user)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            return redirect_role_based(user)
        else:
            return render(request, 'login.html', {'error': 'Invalid email or password.'})
    else:
        return render(request, 'login.html')


def user_logout(request):
    try:
        logout(request)
        return redirect('login')
    except Exception as e:
        print("Error at logout:",e)
        
    


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


@csrf_exempt
def additional_info(request):
    try:
        if request.user.is_authenticated:
            return redirect_role_based(request.user)
        else:
            if request.method == 'POST':
                social_user_info = request.session.get('social_user_info')
                if not social_user_info:
                    return redirect('login')
                
                print(social_user_info)
                
                email = social_user_info['email']
                first_name = social_user_info['first_name']
                last_name = social_user_info['last_name']
                picture_url = social_user_info['picture_url']
                phone = request.POST.get('phone')
                role = request.POST.get('role')
                gender = request.POST.get('gender')
                age = request.POST.get('age')
                pincode = request.POST.get('pincode')

                if not all([phone, role, gender, age, pincode]):
                    return render(request, 'additional_info.html', {'error': 'All fields are required.'})

                if User.objects.filter(phone=phone).exists():
                    return render(request, 'additional_info.html', {'error': 'Phone Number already exists.'})                

                user, created = User.objects.get_or_create(email=email, defaults={
                    'fullname': first_name + " " + last_name,
                    'phone': phone,
                    'role': role,
                    'gender':gender,
                    'age':age,
                    'pincode':pincode
                })
                if created:
                    response = requests.get(picture_url)
                    if response.status_code == 200:
                        user.profile_picture.save(
                            f'{email}_profile.jpg', ContentFile(response.content), save=True)
                    user.set_unusable_password()
                    user.save()

                    login(request, user)
                return redirect_role_based(request.user)
            else:
                return render(request, 'additional_info.html')
    except Exception as e:
        print("Additional Info Exception:", e)
        return render(request, 'additional_info.html', {'error': 'An error occurred. Please try again later.'})


def redirect_role_based(user):
    if user.role == 'attendee':
        return redirect('attendee_dashboard')
    elif user.role == 'organizer':
        return redirect('organizer_dashboard')
    elif user.role == 'administrator':
        return redirect('admin_dashboard')
    else:
        logout(user)
        return redirect('logout')  


# ---------------------------------------------------------------------------------------------------------------------------------------------

# Google Handling Starts

def google_login(request):
    client_id = settings.GOOGLE_CLIENT_ID
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth/oauthchooseaccount?"
        f"client_id={client_id}&redirect_uri=http://127.0.0.1:8000/accounts/google/login/callback/&scope=profile%20email&response_type=code"
    )
    return redirect(auth_url)


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
        user_info_response = requests.get(
            user_info_url, params=user_info_params)
        user_info = user_info_response.json()

        email = user_info.get('email', '')
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        picture = user_info.get('picture', '')

        try:
            user = User.objects.get(email=email)
            if not user.phone or not user.role:
                request.session['social_user_info'] = {
                    'email': email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'picture_url': picture,
                }
                return redirect('additional_info')
            
            login(request, user)
            return redirect_role_based(user)
            
        except User.DoesNotExist:
            request.session['social_user_info'] = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'picture_url': picture,
            }
            return redirect('additional_info')

    except requests.exceptions.RequestException as e:
        print(f"RequestException: {e}")
        return redirect('login')

    except KeyError as e:
        print(f"KeyError: {e}")
        return redirect('login')


# --------------------------------------------------------------------------------------------------------------------------------------


# Github Login


def github_login(request):
    client_id = settings.GITHUB_CLIENT_ID
    redirect_uri = request.build_absolute_uri(reverse('github_callback'))
    auth_url = f"https://github.com/login/oauth/authorize?client_id={
        client_id}&redirect_uri={redirect_uri}&scope=read:user user:email"
    return redirect(auth_url)


def github_callback(request):
    code = request.GET.get('code')

    client_id = settings.GITHUB_CLIENT_ID
    client_secret = settings.GITHUB_CLIENT_SECRET
    token_url = "https://github.com/login/oauth/access_token"
    token_data = {
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': request.build_absolute_uri(reverse('github_callback'))
    }
    headers = {'Accept': 'application/json'}

    try:
        token_response = requests.post(
            token_url, data=token_data, headers=headers)
        token_json = token_response.json()
        access_token = token_json.get('access_token')

        if not access_token:
            return redirect('/')

        # Fetch user info using access token
        user_info_url = "https://api.github.com/user"
        user_info_headers = {'Authorization': f'token {access_token}'}
        user_info_response = requests.get(
            user_info_url, headers=user_info_headers)
        user_info = user_info_response.json()

        if user_info.get('message') == 'Bad credentials':
            print("Invalid access token.")
            return redirect('/')

        email = user_info.get('email')
        if not email:
            emails_url = "https://api.github.com/user/emails"
            emails_response = requests.get(
                emails_url, headers=user_info_headers)
            emails = emails_response.json()
            email = next((item['email']
                         for item in emails if item['primary']), '')

        first_name = user_info.get('name', '').split(' ')[0]
        last_name = user_info.get('name', '').split(' ')[-1]
        avatar_url = user_info.get('avatar_url', '')


        try:
            user = User.objects.get(email=email)    
            if not user.phone or not user.role:
                request.session['social_user_info'] = {
                    'email': email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'picture_url': avatar_url,
                }
                return redirect('additional_info')
            
            login(request, user)
            return redirect_role_based(user)
            
        except User.DoesNotExist:
            request.session['social_user_info'] = {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'picture_url': avatar_url,
            }
            return redirect('additional_info')

    except requests.exceptions.RequestException as e:
        print(f"RequestException: {e}")
        return redirect('login')

    except KeyError as e:
        print(f"KeyError: {e}")
        return redirect('login') 
