from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Booking,Property

@shared_task(name='send_booking_confirmation_email')
def send_booking_confirmation_email(booking_id):
    """send booking confirmation asynchronously"""
    try:
        booking=Booking.objects.select_related('property','user').get(booking_id=booking_id)
        subject=f"Booking confirmation- {Booking.property.name}"

        message=f""" 
                    Dear {booking.user.get_full_name()} 
                    Your booking has been confirmed!
                    Booking Details:
                - Property: {booking.property_obj.name}
                - Check-in: {booking.start_date}
                - Check-out: {booking.end_date}
                - Total Price: ${booking.total_price}
                - Booking Reference: {booking.booking_id}

                Thank you for choosing our service!

                Best regards,
                ALX Travel App Team


                """
        recipient_list=[booking.user.email]
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return f"Confirmation email sent successfully to {booking.user.email}"
    except Booking.DoesNotExist:
        return f"Booking with Id {booking_id} is not found"
    except Exception as e:
        return f"Error sending email: {str(e)}"