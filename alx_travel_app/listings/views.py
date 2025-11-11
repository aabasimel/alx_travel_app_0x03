

from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
import datetime
from datetime import timedelta

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
# from .tasks import send_booking_confirmation_email
from rest_framework import generics, permissions, status, viewsets
from .serializers import *
from django.db.models import Q, Count, Avg, Sum
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView

from rest_framework import generics, permissions, status, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from .auth import EmailTokenObtainPairSerializer
from rest_framework.exceptions import PermissionDenied
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi





class IsOwnerOrReadOnly(permissions.BasePermission):
    """Object-level permission to only allow owneres of an object to edit it."""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'host'):
            return obj.host == request.user
        elif isinstance(obj,User):
            return obj.user==request.user
        return False
class IsHostUser(permissions.BasePermission):
    """Permission to only allow hosts to access certain views."""
    def has_permission(self,request,view):
        return request.user.is_authenticated and request.user.role == 'host'
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'
class IsGuestUser(permissions.BasePermission):
    """Permission to only allow guest users."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'guest'
        
class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes=[permissions.AllowAny]

class ApproveAdminView(APIView):
    permission_classes = [IsAdminUser]  # only admins can approve

    def post(self, request, user_id):
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        if not user.admin_requested:
            return Response({"error": "No admin request found"}, status=400)

        user.role = 'admin'
        user.admin_requested = False
        user.save()
        return Response({"message": f"{user.get_full_name()} is now an admin."})


@extend_schema(
    request=UserLoginSerializer,
    responses={200: UserSerializer},
)
class UserLoginView(APIView):
    """Login view using email to return JWT tokens and user info"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailTokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data, status=status.HTTP_200_OK)
class UserLogoutView(APIView):
    """View for user logout"""
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        
class UserProfileView(generics.RetrieveUpdateAPIView):
    """View for retrieving and updating user profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class UserStatsView(APIView):
    """View for user statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        stats = {
            'total_bookings': Booking.objects.filter(user=user).count(),
            'total_reviews': Review.objects.filter(user=user).count(),
            'upcoming_bookings': Booking.objects.filter(
                user=user, 
                status='confirmed',
                start_date__gte=today
            ).count(),
        }
        
        if user.role == 'host':
            stats['total_properties'] = Property.objects.filter(host=user).count()
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)
class PropertyViewSet(viewsets.ModelViewSet):
    """ViewSet for Property model with custom actions"""
    queryset = Property.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PropertyCreateSerializer
        elif self.action == 'list':
            return PropertyListSerializer
        return PropertyDetailSerializer
    
    def get_queryset(self):
        queryset = Property.objects.all().select_related('host').prefetch_related('reviews').order_by('created_at')

        if self.action == 'list':
            address = self.request.query_params.get('address')
            if address:
                queryset = queryset.filter(address__icontains=address)

            min_price = self.request.query_params.get('min_price')
            max_price = self.request.query_params.get('max_price')
            if min_price:
                queryset = queryset.filter(pricepernight__gte=min_price)
            if max_price:
                queryset = queryset.filter(pricepernight__lte=max_price)

            host_id = self.request.query_params.get('host_id')
            if host_id:
                queryset = queryset.filter(host__user_id=host_id)

        queryset = queryset.annotate(
            average_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        return queryset
    
    def perform_create(self, serializer):
        user=self.request.user
        if user.role not in ['admin','host']:
            raise PermissionDenied("Only admin and host users can create properties. ")
        serializer.save(host=self.request.user)
    
    @action(detail=True, methods=['get'])
    def reviews(self, request, pk=None):
        """Get all reviews for a property"""
        property_obj = self.get_object()
        reviews = property_obj.reviews.all().select_related('user')
        serializer = ReviewListSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        method='get',
        manual_parameters=[
            openapi.Parameter(
                'start_date', openapi.IN_QUERY,
                description="Start date in YYYY-MM-DD format",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'end_date', openapi.IN_QUERY,
                description="End date in YYYY-MM-DD format",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={200: openapi.Response('Availability response')}
    )
    @action(detail=True, methods=['get'],url_path='availability')
    def availability(self, request, pk=None):
        """Check property availability for given dates"""
        property_obj = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response(
                {"error": "Both start_date and end_date are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check for overlapping bookings
        overlapping_bookings = Booking.objects.filter(
            property_obj=property_obj,
            status__in=['pending', 'confirmed'],
            start_date__lt=end_date,
            end_date__gt=start_date
        ).exists()
        
        is_available = not overlapping_bookings
        
        return Response({
            'is_available': is_available,
            'start_date': start_date,
            'end_date': end_date,
            'property': property_obj.name
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsOwnerOrReadOnly])
    def stats(self, request, pk=None):
        """Get statistics for a property (host only)"""
        property_obj = self.get_object()
        
        if property_obj.host != request.user:
            return Response(
                {"error": "You don't have permission to view these statistics"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        
        stats = {
            'total_bookings': Booking.objects.filter(property_obj=property_obj).count(),
            'confirmed_bookings': Booking.objects.filter(
                property_obj=property_obj, 
                status='confirmed'
            ).count(),
            'average_rating': property_obj.reviews.aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0,
            'total_revenue': Booking.objects.filter(
                property_obj=property_obj,
                status='confirmed',
                created_at__gte=thirty_days_ago
            ).aggregate(
                total_revenue=Sum('property_obj__pricepernight')
            )['total_revenue'] or 0,
            'recent_reviews': property_obj.reviews.filter(
                created_at__gte=thirty_days_ago
            ).count()
        }
        
        return Response(stats)
class PropertySearchView(generics.ListAPIView):
    """Advanced property search view"""
    serializer_class = PropertyListSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Property.objects.all().select_related('host').prefetch_related('reviews')
        
        # Search parameters
        location = self.request.query_params.get('location')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        min_rating = self.request.query_params.get('min_rating')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        # Apply filters
        if location:
            queryset = queryset.filter(location__icontains=location)
        
        if min_price:
            queryset = queryset.filter(pricepernight__gte=min_price)
        
        if max_price:
            queryset = queryset.filter(pricepernight__lte=max_price)
        
        if min_rating:
            queryset = queryset.annotate(avg_rating=Avg('reviews__rating')).filter(
                avg_rating__gte=min_rating
            )
        
        # Filter by availability
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                # Exclude properties with overlapping confirmed/pending bookings
                unavailable_properties = Booking.objects.filter(
                    status__in=['pending', 'confirmed'],
                    start_date__lt=end_date,
                    end_date__gt=start_date
                ).values_list('property_obj_id', flat=True)
                
                queryset = queryset.exclude(property_obj_id__in=unavailable_properties)
                
            except ValueError:
                pass
        
        queryset = queryset.annotate(
            average_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        )
        
        return queryset
    @action(detail=False,methods=['delete'],permission_classes=[IsAdminUser])
    def delete_all(self,request):
        """Delete all properties"""
        Property.objects.all().delete()
        count, _ = Property.objects.all().delete()
        return Response(
            {"message": f"Deleted {count} properties successfully."},
            status=status.HTTP_200_OK
        )

# Dashboard Views
class HostDashboardView(APIView):
    """Dashboard view for hosts"""
    permission_classes = [permissions.IsAuthenticated, IsHostUser]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)
        
        # Host properties
        properties = Property.objects.filter(host=user)
        
        # Statistics
        dashboard_data = {
            'total_properties': properties.count(),
            'total_bookings': Booking.objects.filter(property_obj__host=user).count(),
            'pending_bookings': Booking.objects.filter(
                property_obj__host=user,
                status='pending'
            ).count(),
            'revenue_30_days': Booking.objects.filter(
                property_obj__host=user,
                status='confirmed',
                created_at__gte=thirty_days_ago
            ).aggregate(
                total_revenue=Sum('property_obj__pricepernight')
            )['total_revenue'] or 0,
            'average_rating': Review.objects.filter(
                property_obj__host=user
            ).aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
            'recent_reviews': Review.objects.filter(
                property_obj__host=user,
                created_at__gte=thirty_days_ago
            ).count()
        }
        
        # Recent bookings
        recent_bookings = Booking.objects.filter(
            property_obj__host=user
        ).order_by('-created_at')[:5]
        
        # Recent reviews
        recent_reviews = Review.objects.filter(
            property_obj__host=user
        ).order_by('-created_at')[:5]
        
        dashboard_data['recent_bookings'] = BookingListSerializer(recent_bookings, many=True).data
        dashboard_data['recent_reviews'] = ReviewListSerializer(recent_reviews, many=True).data
        
        return Response(dashboard_data)

class GuestDashboardView(APIView):
    """Dashboard view for guests"""
    permission_classes = [permissions.IsAuthenticated, IsGuestUser]
    
    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        dashboard_data = {
            'total_bookings': Booking.objects.filter(user=user).count(),
            'upcoming_trips': Booking.objects.filter(
                user=user,
                status='confirmed',
                start_date__gte=today
            ).count(),
            'total_reviews': Review.objects.filter(user=user).count(),
            'wishlist_count': 0,  # You can add a wishlist feature later
        }
        
        # Upcoming trips
        upcoming_trips = Booking.objects.filter(
            user=user,
            status='confirmed',
            start_date__gte=today
        ).order_by('start_date')[:5]
        
        # Recent bookings
        recent_bookings = Booking.objects.filter(
            user=user
        ).order_by('-created_at')[:5]
        
        dashboard_data['upcoming_trips'] = BookingListSerializer(upcoming_trips, many=True).data
        dashboard_data['recent_bookings'] = BookingListSerializer(recent_bookings, many=True).data
        
        return Response(dashboard_data)
class BookingViewSet(viewsets.ModelViewSet):
    """ViewSet for Booking model"""
    serializer_class = BookingDetailSerializer
    # permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        elif self.action == 'list':
            return BookingListSerializer
        return BookingDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'host':
            # Hosts can see bookings for their properties
            return Booking.objects.filter(
                property_obj__host=user
            ).select_related('property_obj', 'user')
        else:
            # Guests can only see their own bookings
            return Booking.objects.filter(user=user).select_related('property_obj', 'user')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user, status='pending')
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm a booking (host only)"""
        booking = self.get_object()
        
        if booking.property_obj.host != request.user:
            return Response(
                {"error": "Only the property host can confirm bookings"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking.status = 'confirmed'
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel a booking"""
        booking = self.get_object()
        
        # Only the guest who made the booking or the host can cancel
        if booking.user != request.user and booking.property_obj.host != request.user:
            return Response(
                {"error": "You don't have permission to cancel this booking"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        booking.status = 'canceled'
        booking.save()
        
        serializer = self.get_serializer(booking)
        return Response(serializer.data)
    

class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for Review model"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ReviewCreateSerializer
        elif self.action == 'list':
            return ReviewListSerializer
        return ReviewSerializer
    
    def get_queryset(self):
        return Review.objects.all().select_related('property_obj', 'user')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'host':
            # Hosts can see reviews for their properties
            return Review.objects.filter(
                property_obj__host=user
            ).select_related('property_obj', 'user')
        else:
            # Guests can only see their own reviews and all reviews for properties
            return Review.objects.filter(
                Q(user=user) | Q(property_obj__bookings__user=user)
            ).select_related('property_obj', 'user').distinct()


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
    permission_classes = [IsAdminUser]

    def get_serializer(self, *args, **kwargs):
        if action == "create":
            return UserRegistrationSerializer(*args, **kwargs)
        return super().get_serializer(*args,**kwargs)

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