# organizers model.py

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model



User = get_user_model()

class Event(models.Model):
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    name = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    categories = models.CharField(max_length=255)
    event_picture = models.ImageField(upload_to='event_pictures/', blank=True, null=True)
 

    def __str__(self):
        return f"{self.name} - {self.description}"
    

class Ticket(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='ticket_types')
    event_type = models.CharField(max_length=50)  # The general or VIP goes here
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        if not self.pk:  # Only set remaining_quantity for new instances
            self.remaining_quantity = self.quantity
        super(Ticket, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.event.name} - {self.event_type} - {self.price}"


class DynamicPricing(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='dynamic_pricing')
    discount_name = models.CharField(max_length=100, blank=True, null=True)
    discount_code = models.CharField(max_length=20, blank=True, null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    tiered_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    min_quantity_for_tier = models.PositiveIntegerField(blank=True, null=True)

    def is_valid(self):
        now = timezone.now().date()
        return (self.start_date is None or self.start_date <= now) and (self.end_date is None or self.end_date >= now)

    def apply_discount(self, price):
        if self.discount_percentage:
            return price * (1 - (self.discount_percentage / 100))
        return price

    def __str__(self):
        return f"{self.discount_name or 'Tiered Pricing'} - {self.ticket.event}"

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_attendee')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=50, default='Pending')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='event') 
    
    def __str__(self):
        return f"Event: {self.event.name}, Organizer: {self.event.organizer.email}, User: {self.user.email}, Amount: {self.amount}, Status: {self.status}"

# class EventAttendance(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='attendances')
#     event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
#     ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)
#     payment = models.OneToOneField(Payment, on_delete=models.CASCADE)
#     attended = models.BooleanField(default=False)
#     attended_date = models.DateTimeField(blank=True, null=True)

#     def __str__(self):
#         return f"{self.user.email} - {self.event.name} - {self.ticket_type.type}"