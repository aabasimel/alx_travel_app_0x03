"""Module imports for serializers"""

from rest_framework import serializers
from django.utils import timezone
from .models import User, Property, Booking, Review,Payment
from django.contrib.auth import authenticate,get_user_model

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

    property_name = serializers.CharField(source="property.name", read_only=True)
    property_location = serializers.CharField(
        source="property.location", read_only=True
    )
    guest_name = serializers.CharField(source="user.get_full_name", read_only=True)
    total_nights = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()

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
    """Serializer for Booking detail view and creation"""

    property = PropertyListSerializer(read_only=True)
    property_id = serializers.UUIDField(write_only=True)
    user = UserSerializer(read_only=True)
    user_id = serializers.UUIDField(write_only=True)
    total_nights = serializers.ReadOnlyField()
    total_price = serializers.ReadOnlyField()

    class Meta:
        """Booking Detail serializer definition"""

        model = Booking
        fields = [
            "booking_id",
            "property",
            "property_id",
            "user",
            "user_id",
            "start_date",
            "end_date",
            "total_nights",
            "total_price",
            "status",
            "created_at",
        ]
        read_only_fields = ["booking_id", "created_at"]

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        property_id = attrs.get("property_id")

        if start_date and end_date:
            if start_date >= end_date:
                raise serializers.ValidationError("End date must be after start date.")

            # Check for overlapping bookings if property is provided
            if property_id:
                # pylint: disable=no-member
                overlapping_bookings = Booking.objects.filter(
                    property_id=property_id,
                    status__in=["pending", "confirmed"],
                    start_date__lt=end_date,
                    end_date__gt=start_date,
                )

                # Exclude current booking if updating
                if self.instance:
                    overlapping_bookings = overlapping_bookings.exclude(
                        booking_id=self.instance.booking_id
                    )

                if overlapping_bookings.exists():
                    raise serializers.ValidationError(
                        "Property is not available for the selected dates."
                    )

        return attrs

    def validate_user_id(self, value):
        """Validate user's id"""
        try:
            user = User.objects.get(user_id=value)
            if user.role not in ["guest", "admin"]:
                raise serializers.ValidationError("Only guests can make bookings.")
        except User.DoesNotExist as exc:  # pylint: disable=no-member
            raise serializers.ValidationError("Guest not found.") from exc
        return value

    def validate_property_id(self, value):
        """Validate property's id"""
        try:
            Property.objects.get(property_id=value)  # pylint: disable=no-member
        except Property.DoesNotExist as exc:  # pylint: disable=no-member
            raise serializers.ValidationError("Property not found.") from exc
        return value


class ReviewSerializer(serializers.ModelSerializer):
    """Serializer for Review model"""

    property_name = serializers.CharField(source="property.name", read_only=True)
    reviewer_name = serializers.CharField(source="user.get_full_name", read_only=True)
    property_id = serializers.UUIDField(write_only=True)
    user_id = serializers.UUIDField(write_only=True)

    class Meta:
        """Review model serializer definition"""

        model = Review
        fields = [
            "review_id",
            "property_name",
            "reviewer_name",
            "property_id",
            "user_id",
            "rating",
            "comment",
            "created_at",
        ]
        read_only_fields = ["review_id", "created_at"]

    def validate(self, attrs):
        property_id = attrs.get("property_id")
        user_id = attrs.get("user_id")

        # Check if user has a confirmed booking for this property
        if property_id and user_id:
            has_booking = Booking.objects.filter(  # pylint: disable=no-member
                property_id=property_id,
                user_id=user_id,
                status="confirmed",
                end_date__lt=timezone.now().date(),  # Booking must be completed
            ).exists()

            if not has_booking:
                raise serializers.ValidationError(
                    "You can only review properties you have stayed at."
                )

        return attrs

    def validate_property_id(self, value):
        """Validate property's id"""
        try:
            Property.objects.get(property_id=value)  # pylint: disable=no-member
        except Property.DoesNotExist as exc:  # pylint: disable=no-member
            raise serializers.ValidationError("Property not found.") from exc
        return value

    def validate_user_id(self, value):
        """Validate user's id"""
        try:
            User.objects.get(user_id=value)
        except User.DoesNotExist as exc:  # pylint: disable=no-member
            raise serializers.ValidationError("User not found.") from exc
        return value
class PaymentSerializer(serializers.ModelSerializer):
    booking = BookingListSerializer(read_only=True)
    booking_id = serializers.UUIDField(write_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'payment_id', 'booking', 'booking_id', 'amount', 'transaction_id',
            'reference', 'status', 'status_display', 'payment_method',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'payment_id', 'transaction_id', 'status', 'reference',
            'created_at', 'updated_at'
        ]

    def validate_booking_id(self, value):
        """Validate that the booking exists and doesn't already have a payment"""
        try:
            booking = Booking.objects.get(booking_id=value)
        except Booking.DoesNotExist:
            raise serializers.ValidationError("Booking not found.")

        if hasattr(booking, 'payment'):
            raise serializers.ValidationError("Payment already exists for this booking.")

        return value

    def validate_amount(self, value):
        """Ensure amount is positive"""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value