# attendee/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from organizer.models import Payment, Event, Ticket
import stripe
from django.contrib import messages


@login_required
def create_checkout_session(request):
    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        ticket_id = request.POST.get('ticket_id')
        quantity = int(request.POST.get('quantity'))

        event = get_object_or_404(Event, id=event_id)
        ticket = get_object_or_404(Ticket, id=ticket_id)
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

    return redirect('home') 

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
                ticket = get_object_or_404(Ticket, id=ticket_id)
                remain_quantity = ticket.quantity - quantity
                ticket.remaining_quantity = remain_quantity
                ticket.save()

                messages.success(request, 'Payment successful!')
            else:
                messages.error(request, 'Payment failed.')

        except Payment.DoesNotExist:
            messages.error(request, 'Payment record not found.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')

    return redirect('index')

@login_required
def payment_cancel(request):
    messages.error(request, 'Payment was cancelled.')
    return redirect('index')


def home(request):
    event_details = []
    events = Event.objects.all()
    for event in events:
        tickets = Ticket.objects.filter(event=event)
        event_details.append({'event': event, 'tickets': tickets})
    
    return render(request, 'dashboard.html', {'event_details': event_details})