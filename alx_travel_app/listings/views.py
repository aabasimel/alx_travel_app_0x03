"""Module imports for viewsets"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from django_filters.rest_framework import DjangoFilterBackend
from .models import Property, Booking, Review, User,Payment
from .serializers import (
    PropertyListSerializer,
    PropertyDetailSerializer,
    BookingListSerializer,
    BookingDetailSerializer,
    ReviewSerializer,
    UserSerializer,
    PaymentSerializer
)
import os
import requests
from rest_framework.permissions import IsAuthenticated
# from .tasks import send_booking_confirmation_email



class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["host", "location"]
    search_fields = ["name", "description", "location"]
    ordering_fields = ["pricepernight", "created_at", "name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == "list":
            return PropertyListSerializer
        return PropertyDetailSerializer

    @action(detail=True, methods=["get"])
    def bookings(self, request, pk=None):
        """Get all bookings for a specific property"""
        property_obj = self.get_object()
        bookings = property_obj.bookings.all()
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        """Get all reviews for a specific property"""
        property_obj = self.get_object()
        reviews = property_obj.reviews.all()
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)


class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["property_obj", "user", "status"]
    ordering_fields = ["start_date", "end_date", "created_at"]
    ordering = ["created_at"]

    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == "list":
            return BookingListSerializer
        return BookingDetailSerializer

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Confirm a pending booking"""
        booking = self.get_object()
        if booking.status != "pending":
            return Response(
                {"error": "Only pending bookings can be confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = "confirmed"
        booking.save()
        serializer = BookingDetailSerializer(booking)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        if booking.status == "canceled":
            return Response(
                {"error": "Booking is already canceled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = "canceled"
        booking.save()
        serializer = BookingDetailSerializer(booking)
        return Response(serializer.data)
    # def perform_create(self, serializer):
    #     booking=serializer.save(user=self.request.user)
    #     send_booking_confirmation_email.delay(booking.booking_id)


class ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Review model providing CRUD operations.
    """

    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["listing_id", "user", "rating"]
    ordering_fields = ["rating", "created_at"]
    ordering = ["-created_at"]


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for User model providing CRUD operations.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["role"]
    search_fields = ["first_name", "last_name", "email"]
    ordering_fields = ["first_name", "last_name", "created_at"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["get"])
    def properties(self, request, pk=None):
        """Get all properties for a specific host"""
        user = self.get_object()
        if user.role not in ["host", "admin"]:
            return Response(
                {"error": "User is not a host or admin."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        properties = user.properties.all()
        serializer = PropertyListSerializer(properties, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def bookings(self, request, pk=None):
        """Get all bookings for a specific user"""
        user = self.get_object()
        bookings = user.bookings.all()
        serializer = BookingListSerializer(bookings, many=True)
        return Response(serializer.data)
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'], url_path='initiate')
    def initiate_payment(self, request):
        """Initiate payment with Chapa"""
        booking_id = request.data.get('booking_id')

        try:
            booking = Booking.objects.get(booking_id=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

        # Create payment record
        payment = Payment.objects.create(
            booking=booking,
            amount=booking.total_price,
            reference=f"BK-{booking.booking_id}"
        )

        # Prepare Chapa payment request
        chapa_url = "https://api.chapa.co/v1/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {os.getenv('CHAPA_SECRET_KEY')}",
            "Content-Type": "application/json"
        }

        payload = {
            "amount": str(booking.total_price),
            "currency": "ETB",
            "email": request.user.email,
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "tx_ref": payment.reference,
            "callback_url": request.build_absolute_uri('/api/payments/verify/'),
            "return_url": request.data.get('return_url', 'http://localhost:3000/payment/success'),
            "customization": {
                "title": f"Payment for {booking.listing.title}",
                "description": f"Booking from {booking.check_in_date} to {booking.check_out_date}"
            }
        }

        try:
            response = requests.post(chapa_url, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and response_data.get('status') == 'success':
                payment.transaction_id = response_data['data']['tx_ref']
                payment.save()

                return Response({
                    'payment_url': response_data['data']['checkout_url'],
                    'reference': payment.reference,
                    'status': 'success'
                }, status=status.HTTP_200_OK)
            else:
                payment.status = 'failed'
                payment.save()
                return Response({'error': response_data.get('message', 'Payment initiation failed')},
                                status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            payment.status = 'failed'
            payment.save()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='verify')
    def verify_payment(self, request):
        """Verify payment status with Chapa"""
        tx_ref = request.query_params.get('tx_ref')

        if not tx_ref:
            return Response({'error': 'Transaction reference is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(reference=tx_ref)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        # Verify with Chapa
        chapa_url = f"https://api.chapa.co/v1/transaction/verify/{tx_ref}"
        headers = {
            "Authorization": f"Bearer {os.getenv('CHAPA_SECRET_KEY')}"
        }

        try:
            response = requests.get(chapa_url, headers=headers)
            response_data = response.json()

            if response.status_code == 200 and response_data.get('status') == 'success':
                chapa_status = response_data['data']['status']

                if chapa_status == 'success':
                    payment.status = 'completed'
                    payment.booking.status = 'confirmed'
                    payment.booking.save()
                else:
                    payment.status = 'failed'

                payment.save()

                return Response({
                    'reference': payment.reference,
                    'status': payment.status,
                    'amount': str(payment.amount)
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Verification failed'},
                                status=status.HTTP_400_BAD_REQUEST)

        except requests.exceptions.RequestException as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)