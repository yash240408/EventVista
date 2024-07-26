# attendee/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from organizer.models import Payment, Event, Ticket
import stripe, qrcode, json
from django.contrib import messages
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.db import transaction


@login_required
def create_checkout_session(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        ticket_id = request.POST.get('ticket_id')
        quantity = int(request.POST.get('quantity'))

        event = get_object_or_404(Event, id=event_id)
        ticket = get_object_or_404(Ticket, id=ticket_id)
        
        if quantity > ticket.remaining_quantity:
            messages.error(request, f'Only {ticket.remaining_quantity} tickets are available for this event.')
            return redirect('attendee_dashboard')

        amount = ticket.price * quantity 

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'{event.name} - {ticket.event_type} Ticket',
                        },
                        'unit_amount': int(ticket.price * 100), 
                    },
                    'quantity': quantity,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/attendee/payment-success/') + '?session_id={CHECKOUT_SESSION_ID}',
                cancel_url=request.build_absolute_uri('/attendee/payment-cancel/'),
                metadata={'user_id': request.user.id, 'event_id': event.id, 'ticket_id': ticket.id, 'quantity': quantity}
            )
            Payment.objects.create(
                user=request.user,
                event=event,
                amount=amount,
                transaction_id=session.id,
                status='Pending'
            )

            return redirect(session.url, code=303)
        
        except Exception as e:
            return render(request, 'payment_error.html', {'error': str(e)})

    return redirect('attendee_dashboard')


@login_required
def payment_success(request):
    session_id = request.GET.get('session_id')
    if session_id:
        try:
            # Retrieve the Stripe session
            session = stripe.checkout.Session.retrieve(session_id)

            # Retrieve the Payment object
            payment = Payment.objects.get(transaction_id=session_id)

            # Update payment status
            payment.status = 'Completed' if session.payment_status == 'paid' else 'Failed'
            payment.save()

            metadata = session.metadata
            event_id = metadata.get('event_id')
            ticket_id = metadata.get('ticket_id')
            quantity = int(metadata.get('quantity'))

            if payment.status == 'Completed':
                # Use atomic transaction to ensure data consistency
                with transaction.atomic():
                    ticket = get_object_or_404(Ticket, id=ticket_id)
                    event = ticket.event

                    # Check if there is enough quantity available
                    if ticket.remaining_quantity < quantity:
                        messages.error(request, 'Not enough tickets available.')
                        return redirect('attendee_dashboard')

                    # Update ticket remaining quantity
                    ticket.remaining_quantity -= quantity
                    ticket.save()

                # Generate QR code
                try:
                    qr_data = {
                        "Attendee Name": request.user.fullname,
                        "Attendee Email": request.user.email,
                        "Payment Status": payment.status,
                        "Payment Date": payment.payment_date.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    qr_code_img = qrcode.make(json.dumps(qr_data))
                    
                    qr_code_filename = f"Event_Pass_{request.user.fullname}.png"
                    qr_code_path = f"media/qrcodes/{qr_code_filename}"
                    qr_code_img.save(qr_code_path)

                    context = {
                        'event_name': event.name,
                        'event_date': event.date,
                        'event_time': event.time,
                        'event_location': event.location,
                        'quantity': quantity,
                        'ticket_price': ticket.price,
                        'total_price': quantity * ticket.price,
                    }
                    email_body = render_to_string('email_template.html', context)
                    email_subject = f"Your Tickets for {event.name}"

                    email = EmailMessage(
                        email_subject,
                        email_body,
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email]
                    )
                    email.content_subtype = 'html'

                    with open(qr_code_path, 'rb') as qr_code_file:
                        email.attach(qr_code_filename, qr_code_file.read(), 'image/png')
                    email.send()
                except Exception as e:
                    print(f"QR Code or Email Error: {e}")
                    messages.error(request, 'An error occurred while generating the QR code or sending the email.')

                messages.success(request, 'Payment successful! A confirmation email has been sent.')
            else:
                messages.error(request, 'Payment failed.')

        except Payment.DoesNotExist:
            messages.error(request, 'Payment record not found.')
        except Exception as e:
            print(f"General Error: {e}")
            messages.error(request, f'An error occurred: {str(e)}')

    return redirect('attendee_dashboard')

@login_required
def payment_cancel(request):
    messages.error(request, 'Payment was cancelled.')
    return redirect('attendee_dashboard')

@login_required
def home(request):
    events = Event.objects.all().order_by('categories', 'date', 'time')
    categories = Event.objects.values_list('categories', flat=True).distinct()
    event_data = {}
    
    for category in categories:
        event_data[category] = []
        category_events = events.filter(categories=category)
        for event in category_events:
            tickets = Ticket.objects.filter(event=event)
            for ticket in tickets:
                event_data[category].append({
                    'event_id':event.id,
                    'event_name': event.name,
                    'description': event.description,
                    'date_time': f"{event.date} {event.time}",
                    'location': event.location,
                    'category': event.categories,
                    'event_picture': event.event_picture.url if event.event_picture else '',
                    'ticket_type': ticket.event_type,
                    'ticket_price': ticket.price,
                    'remaining_quantity': ticket.remaining_quantity,
                })
    
    context = {
        'event_data': event_data,
        'categories': categories,
    }    
    return render(request, 'attendee_dashboard.html', context)


@login_required
def event_history(request):
    payments = Payment.objects.filter(user=request.user)
    event_details = []

    for payment in payments:
        event = payment.event
        ticket = Ticket.objects.filter(event=event)
        event_details.append({
            'event': event,
            'ticket': ticket,
            'payment': payment 
        }) 
    return render(request, 'attendee_orderhistory.html', {'event_details': event_details})


@login_required
def event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    ticket = Ticket.objects.filter(event=event).first() 
    context = {
        'event': event,
        'ticket': ticket,
    }  
    return render(request, 'attendee_event.html', context)



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
        return redirect('attendee_dashboard')

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
    
    return render(request, 'attendee_profile.html', {'user_details': user_details})
