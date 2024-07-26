# organizer/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.conf import settings
import stripe, time as picture_time
from organizer.models import Event, Ticket, Payment, User
from django.contrib import messages
from django.db.models import Sum, Count,  Max, Min, Avg
from datetime import timedelta
stripe.api_key = settings.STRIPE_SECRET_KEY
from django.utils import timezone
import matplotlib.pyplot as plt
import io, base64

@login_required
def home(request):
    if request.user.is_authenticated:
        # Fetching the organizer's events
        events = Event.objects.filter(organizer=request.user)
        
        # Fetching payments for those events
        last_payments = Payment.objects.filter(event__in=events)
        payments = Payment.objects.filter(event__in=events, status='Completed')
        
        # Fetching the last 10 payments
        last_10_payments = last_payments.order_by('-payment_date')[:10]
        
        # Analytics for payments
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        today_payments = payments.filter(payment_date__date=today).aggregate(total=Sum('amount'))['total'] or 0
        yesterday_payments = payments.filter(payment_date__date=yesterday).aggregate(total=Sum('amount'))['total'] or 0
        
        # Analytics for monthly sales
        monthly_sales = payments.filter(payment_date__year=today.year, payment_date__month=today.month).aggregate(total_sales=Sum('amount'))['total_sales'] or 0
        total_orders = payments.count()
        avg_order_value = (monthly_sales / total_orders) if total_orders > 0 else 0
        
        # Age and gender analytics
        users = User.objects.filter(payment_attendee__in=payments).distinct()
        age_data = users.aggregate(min_age=Min('age'), max_age=Max('age'), avg_age=Avg('age'))
        gender_counts = users.values('gender').annotate(count=Count('gender')).order_by('gender')
        
        # Data for charts
        sales_data = [payment.amount for payment in last_10_payments]
        sales_labels = [payment.payment_date.strftime('%d-%m-%Y') for payment in last_10_payments]
        
        age_labels = ['Min Age', 'Avg Age', 'Max Age']
        age_values = [age_data['min_age'] or 0, age_data['avg_age'] or 0, age_data['max_age'] or 0]
        
        gender_labels = [gender['gender'] for gender in gender_counts]
        gender_values = [gender['count'] for gender in gender_counts]

        # Create and save charts
        def create_chart(data, labels, title):
            fig, ax = plt.subplots()
            ax.bar(labels, data)
            ax.set_title(title)
            ax.set_xlabel('Date')
            ax.set_ylabel('Amount')
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            return base64.b64encode(buf.getvalue()).decode('utf-8')
        
        def create_line_chart(data1, labels1, data2, labels2, title):
            fig, ax = plt.subplots()
            ax.plot(labels1, data1, label='Age Distribution')
            ax.plot(labels2, data2, label='Gender Distribution')
            ax.set_title(title)
            ax.set_xlabel('Categories')
            ax.set_ylabel('Values')
            ax.legend()
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)
            return base64.b64encode(buf.getvalue()).decode('utf-8')

        # Chart images
        sales_chart_img = create_chart(sales_data, sales_labels, 'Monthly Sales')
        line_chart_img = create_line_chart(age_values, age_labels, gender_values, gender_labels, 'Age and Gender Distribution')
        
        context = {
            'fullname': request.user.fullname if hasattr(request.user, 'fullname') else None,
            'role': request.user.role if hasattr(request.user, 'role') else None,
            'today_payments': today_payments,
            'yesterday_payments': yesterday_payments,
            'monthly_sales': monthly_sales,
            'total_orders': total_orders,
            'avg_order_value': avg_order_value,
            'sales_chart_img': sales_chart_img,
            'line_chart_img': line_chart_img,
            'payment_history':last_10_payments
        }
        return render(request, "organizer_home.html", context)
    else:
        return redirect('login', {'error': 'Please Login First'})

@login_required
def add_event(request):
    if request.method == 'POST':
        name = request.POST.get("name")
        description = request.POST.get("description")
        date = request.POST.get("date")
        time = request.POST.get("time")
        location = request.POST.get("location")
        categories = request.POST.get("categories")
        ticket_type = request.POST.get("ticket_type")
        ticket_price = request.POST.get("ticket_price")
        ticket_quantity = request.POST.get("ticket_quantity")
        event_picture = request.FILES.get('event_picture')

        if not all([name, description, date, time, location, categories, ticket_type, ticket_price, ticket_quantity, event_picture]):
            return render(request, 'organizer_Addevent.html', {'error': 'All fields are required.'})
        
        timestamp = int(picture_time.time())
        original_extension = event_picture.name.split('.')[-1]
        new_file_name = f"{timestamp}.{original_extension}"
        event_picture.name = new_file_name

        event = Event.objects.create(
            organizer=request.user,
            name=name,
            description=description,
            date=date,
            time=time,
            location=location,
            categories=categories,
            event_picture=event_picture
        )


        Ticket.objects.create(
            event=event,
            event_type=ticket_type,
            price=float(ticket_price),
            quantity=int(ticket_quantity),
        )

        messages.success(request, 'Event created successfully!')
        return redirect('events_list')

    return render(request, 'organizer_Addevent.html')


@login_required
def events_list(request):
    # Get all events organized by the logged-in user
    events = Event.objects.filter(organizer=request.user)

    # Prepare a list to hold event details along with their tickets
    event_details = []
    for event in events:
        tickets = Ticket.objects.filter(event=event)
        event_details.append({
            'event': event,
            'tickets': tickets
        })

    return render(request, 'organizer_Events.html', {'event_details': event_details})

@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer=request.user)
    ticket = get_object_or_404(Ticket, event_id=event_id)

    if request.method == 'POST':
        event.name = request.POST.get("name")
        event.description = request.POST.get("description")
        event.date = request.POST.get("date")
        event.time = request.POST.get("time")
        event.location = request.POST.get("location")
        event.categories = request.POST.get("categories")

        ticket.event_type = request.POST.get("ticket_type")
        ticket.price = request.POST.get("ticket_price")
        ticket.quantity = request.POST.get("ticket_quantity")



        if not all([event.name, event.description, event.location, event.categories, ticket.event_type, ticket.price, ticket.quantity]):
            return render(request, 'organizer_Editevent.html', {'event': event, 'ticket':ticket,'error': 'All fields are required.'})
        
        event_picture = request.FILES.get('event_picture')
        if event_picture:
            event.event_picture = event_picture

        event.save()
        ticket.save()

        messages.success(request, 'Event updated successfully!')
        return redirect('events_list')

    return render(request, 'organizer_Editevent.html', {'event': event, 'ticket':ticket})

@login_required
def payment_details(request):
    organized_events = Event.objects.filter(organizer=request.user)
    payments = Payment.objects.filter(event__in=organized_events)
    return render(request, 'organizer_payment.html', {'payments': payments})



@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, organizer=request.user)
    Ticket.objects.filter(event=event).delete()
    event.delete()
    messages.success(request, 'Event and associated tickets deleted successfully!')
    return redirect('events_list')



@login_required
def profile(request):
    user = request.user
    
    if request.method == 'POST':
        # Retrieve data from form submission
        fullname = request.POST.get('fullname')
        pincode = request.POST.get('pincode')
        gender = request.POST.get('gender')
        age = request.POST.get('age')
        profile_picture = request.FILES.get('profile_picture')

        if fullname:
            user.fullname = fullname
        if pincode:
            user.pincode = pincode
        if gender:
            user.gender = gender
        if age:
            try:
                user.age = int(age)
            except ValueError:
                pass
        
        if profile_picture:
            user.profile_picture = profile_picture
        
        user.save()
        
        # Redirect to profile page after saving
        return redirect('organizer_dashboard')

    user_details = {
        'fullname': user.fullname,
        'email': user.email,
        'phone': user.phone,
        'role': user.role,
        'profile_picture': user.profile_picture.url if user.profile_picture else None,
        'pincode': user.pincode,
        'gender': user.gender,
        'age': user.age
    }
    
    return render(request, 'organizer_profile.html', {'user_details': user_details})

@login_required
def event_share(request):
    events = Event.objects.filter(organizer=request.user)
    return render(request, 'organizer_share.html', {'events': events})

def public_event_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    ticket = Ticket.objects.filter(event=event).first() 
    return render(request, "public_event_details.html", {'event': event, 'ticket': ticket})