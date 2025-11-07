"""Module imports for serializers"""

from rest_framework import serializers
from django.utils import timezone
from .models import User, Property, Booking, Review,Payment
from django.contrib.auth import authenticate,get_user_model
import uuid

class UserRegistrationSerializer (serializers.ModelSerializer):
    """Serializer for user registration"""
    password=serializers.CharField(write_only=True,min_length=8)
    password_confirm=serializers.CharField(write_only=True,min_length=8)

    class Meta:
        model=User
        fields = ('user_id', 'first_name', 'last_name', 'email', 'phone_number', 
                 'role', 'password', 'password_confirm', 'created_at')
        read_only_fields=[
            'user_id',
            'created_at',

        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

        def validate(self,attrs):
            password=attrs.get('password')
            confirm_password=attrs.get('password_confirm')

            if password !=confirm_password:
                raise serializers.ValidationError("password doesn't match")
            
            return attrs
        
        def create(self,validated_data):
            validated_data.pop('password_confirm')
            password=validated_data.pop('password')
            user=User.objects.create(password=password,**validated_data)
            return user

class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email=serializers.EmailField()
    password=serializers.CharField(write_only=True)

    def validate(self, attrs):
        email=attrs.get('email')
        password=attrs.get('password')
        if email and password:
            user = authenticate(username=email, password=password)  # This might work!
            if not user:
                raise serializers.ValidationError('Invalid email or password')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        raise serializers.ValidationError('Email and password are required')


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        """User serializer definition"""

        model = User
        fields = [
            "user_id",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone_number",
            "role",
            "created_at",
        ]
        read_only_fields = ["user_id", "created_at","email","phone_number"]

    def get_full_name(self, obj):
        """Get user's full name"""
        return f"{obj.first_name} {obj.last_name}"


class PropertyListSerializer(serializers.ModelSerializer):
    """Serializer for Property list view (minimal data)"""

    host_name = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        """Property List serializer definition"""

        model = Property
        fields = [
            "property_id",
            "name",
            "location",
            "pricepernight",
            "host_name",
            "average_rating",
            "review_count",
            "created_at",
        ]

    def get_host_name(self, obj):
        """Get host's name"""
        return obj.host.get_full_name()

    def get_average_rating(self, obj):
        """Calculate the average rating for a property"""
        reviews = obj.reviews.all()
        if reviews:
            return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return None

    def get_review_count(self, obj):
        """Count total reviews"""
        return obj.reviews.count()


class PropertyDetailSerializer(serializers.ModelSerializer):
    """Serializer for Property detail view (complete data)"""

    host = UserSerializer(read_only=True)
    host_id = serializers.UUIDField(write_only=True)
    average_rating = serializers.SerializerMethodField(read_only=True)
    review_count = serializers.SerializerMethodField(read_only=True)
    total_nights_booked = serializers.SerializerMethodField()

    class Meta:
        """Property Detail serializer definition"""

        model = Property
        fields = '__all__'
        read_only_fields = ["property_id", "created_at", "updated_at"]

    def get_average_rating(self, obj):
        """Calculate the average rating for a property"""
        reviews = obj.reviews.all()
        if reviews:
            return round(sum(r.rating for r in reviews) / len(reviews), 1)
        return None

    def get_review_count(self, obj):
        """Count total reviews"""
        return obj.reviews.count()

    def get_total_nights_booked(self, obj):
        """Calculate total nights booked"""
        confirmed_bookings = obj.bookings.filter(status="confirmed")
        return sum(booking.total_nights for booking in confirmed_bookings)

    def validate_host_id(self, value):
        """Validate host's id"""
        try:
            host = User.objects.get(user_id=value)
            if host.role not in ["host", "admin"]:
                raise serializers.ValidationError(
                    "User must be a host or admin to create properties."
                )
        except User.DoesNotExist as exc:  # pylint: disable=no-member
            raise serializers.ValidationError("Host not found.") from exc
        return value
class ProperyCreateSerializer(serializers.ModelSerializer):
    """serializer for property creation"""
    class Meta:
        model=Property
        fileds=('name','description','amenities','address','city','country','pricepernight')
    def create(self, validated_data):
        return Property.objects.create(**validated_data)
class BookingListSerializer(serializers.ModelSerializer):
    """Serializer for Booking list view"""

    property_name = serializers.CharField(source="property_obj.name", read_only=True)
    property_address = serializers.CharField(
        source="property_obj.address", read_only=True
    )
    guest_name = serializers.CharField(source="user.get_full_name", read_only=True)
    total_nights = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()
    city=serializers.ReadOnlyField()
    country=serializers.ReadOnlyField()


    class Meta:
        """Booking List serialier definition"""

        model = Booking
        fields = [
            "booking_id",
            "property_name",
            "property_location",
            "guest_name",
            "start_date",
            "end_date",
            "total_nights",
            "total_price",
            "status",
            "created_at",
        ]


class BookingDetailSerializer(serializers.ModelSerializer):
    """Serializer for booking detail view"""
    property_name = serializers.CharField(source='property_obj.name', read_only=True)
    property_location = serializers.CharField(source='property_obj.location', read_only=True)
    property_price = serializers.DecimalField(source='property_obj.pricepernight', 
                                            max_digits=10, decimal_places=2, read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    total_nights = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('booking_id', 'property_obj', 'user', 'created_at')

class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer for Booking creation"""

    property_list = PropertyListSerializer(source='property_obj', read_only=True)
    property_id = serializers.UUIDField(write_only=True)
    user = UserSerializer(read_only=True)
    total_nights = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = Booking
        fields = [
            "booking_id",
            "property_list", 
            "user",
            "property_id",
            "start_date",
            "end_date",
            "total_nights",
            "total_price",
            "status",
            "created_at",
        ]
        read_only_fields = ["booking_id", "created_at", "status", "user"]

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("End date must be after start date")
        
        property_id = attrs.get('property_id')
        if property_id and start_date and end_date:
            try:
                property_obj = Property.objects.get(property_id=property_id)
                
                # Check if property is available
                if not property_obj.is_available:
                    raise serializers.ValidationError("Property is not available for booking.")
                
                # Check for overlapping bookings
                overlapping_bookings = Booking.objects.filter(
                    property_obj=property_obj,
                    status__in=['pending', 'confirmed'],
                    start_date__lt=end_date,
                    end_date__gt=start_date
                )
                if overlapping_bookings.exists():
                    raise serializers.ValidationError("Property is not available for the selected dates")
                    
            except Property.DoesNotExist:
                raise serializers.ValidationError("Property not found")
        
        return attrs

    def validate_property_id(self, value):
        """Validate property exists"""
        try:
            Property.objects.get(property_id=value)
        except Property.DoesNotExist:
            raise serializers.ValidationError("Property not found.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        property_id = validated_data.pop('property_id')
        property_obj = Property.objects.get(property_id=property_id)
        
        # Set default status
        validated_data.setdefault('status', 'pending')
        
        # Create the booking
        booking = Booking.objects.create(
            property_obj=property_obj,
            user=user,
            **validated_data
        )
        
        # Check if this booking makes the property unavailable (has overlapping bookings)
        self.update_property_availability(property_obj)
        
        return booking

    def update_property_availability(self, property_obj):
        """Update property availability based on overlapping bookings"""
        # Check if there are any active bookings (pending or confirmed)
        active_bookings = Booking.objects.filter(
            property_obj=property_obj,
            status__in=['pending', 'confirmed']
        ).exists()
        
        # Update property availability
        if active_bookings:
            property_obj.is_available = False
        else:
            property_obj.is_available = True
            
        property_obj.save()

class ReviewListSerializer(serializers.ModelSerializer):
    """Serializer for review listing"""
    property_name = serializers.CharField(source='property_obj.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Review
        fields = ('review_id', 'property_name', 'user_name', 'rating', 
                 'comment', 'created_at')
        
class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for review detail view"""
    property_name = serializers.CharField(source='property_obj.name', read_only=True)
    property_location = serializers.CharField(source='property_obj.location', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Review
        fields = '__all__'
        read_only_fields = ('review_id', 'property_obj', 'user', 'created_at')

class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating reviews"""
    
    class Meta:
        model = Review
        fields = ('property_obj', 'rating', 'comment')
    
    def validate(self, attrs):
        user = self.context['request'].user
        property_obj = attrs.get('property_obj')
        
        # Check if user has already reviewed this property
        if Review.objects.filter(user=user, property_obj=property_obj).exists():
            raise serializers.ValidationError("You have already reviewed this property")
        
        # Check if user has actually booked this property
        has_booking = Booking.objects.filter(
            user=user, 
            property_obj=property_obj,
            status='confirmed',
            end_date__lt=timezone.now().date()  # Only allow reviews after stay
        ).exists()
        
        if not has_booking:
            raise serializers.ValidationError("You can only review properties you have stayed at")
        
        return attrs
    
    def create(self, validated_data):
        # The user will be set from the request user in the view
        return Review.objects.create(**validated_data)
    
class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payments"""
    booking_details = BookingListSerializer(source='booking', read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('payment_id', 'created_at', 'updated_at')


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating payments"""
    
    class Meta:
        model = Payment
        fields = ('booking', 'amount', 'payment_method')
        read_only_fields = ('amount',)
    
    def validate(self, attrs):
        booking = attrs.get('booking')
        
        # Auto-set amount from booking
        if booking:
            attrs['amount'] = booking.total_price
        
        # Generate unique reference
        attrs['reference'] = f"CHAPA-{uuid.uuid4().hex[:12].upper()}"
        
        return attrs


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    total_bookings = serializers.IntegerField()
    total_reviews = serializers.IntegerField()
    total_properties = serializers.IntegerField()
    upcoming_bookings = serializers.IntegerField()


class PropertyStatsSerializer(serializers.Serializer):
    """Serializer for property statistics"""
    total_bookings = serializers.IntegerField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    occupancy_rate = serializers.DecimalField(max_digits=5, decimal_places=2)