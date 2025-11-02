"""Module imports for model creation"""

import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


class User(AbstractUser):
    """Custom User model matching the SQL schema"""

    ROLE_CHOICES = [
        ("guest", "Guest"),
        ("host", "Host"),
        ("admin", "Admin"),
    ]

    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="guest")
    created_at = models.DateTimeField(auto_now_add=True)

    # Override username field since we're using email
    username = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        """User table definition"""

        db_table = "user"
        indexes = [
            models.Index(fields=["email"], name="idx_user_email"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        """Return the user's first name."""
        return self.first_name


class Property(models.Model):
    """Property model matching the SQL schema"""

    property_obj_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    host = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="properties",
        db_column="host_id",
    )
    name = models.CharField(max_length=150)
    description = models.TextField()
    location = models.CharField(max_length=255)
    pricepernight = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Property table definition"""

        db_table = "property"
        indexes = [
            models.Index(fields=["host"], name="idx_property_host"),
            models.Index(fields=["property_obj_id"], name="idx_property_id"),
            models.Index(fields=["location"], name="idx_property_location"),
        ]

    def __str__(self):
        return f"{self.name} - {self.location}"


class Booking(models.Model):
    """Booking model matching the SQL schema"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("canceled", "Canceled"),
    ]

    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_obj = models.ForeignKey(
        "Property",
        on_delete=models.CASCADE,
        related_name="bookings",
        db_column="property_id",
    )
    user = models.ForeignKey(
        "User", on_delete=models.CASCADE, related_name="bookings", db_column="user_id"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Booking table definition"""

        db_table = "booking"
        indexes = [
            models.Index(fields=["property_obj"], name="idx_booking_property"),
            models.Index(fields=["user"], name="idx_booking_user"),
        ]

    def clean(self):

        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")

    @property
    def total_nights(self):
        """Calculating number of nights"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return 0

    @property
    def total_price(self):
        """Calculating total price"""
        # pylint: disable=no-member
        return self.total_nights * self.property_obj.pricepernight

    def __str__(self):
        return f"#{self.booking_id} - {self.property_obj.name} ({self.start_date} to {self.end_date})"


class Review(models.Model):
    """Review model matching the SQL schema"""

    review_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    property_obj = models.ForeignKey(
        "Property",
        on_delete=models.CASCADE,
        related_name="reviews",
        db_column="property_id",
    )
    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="reviews",
        db_column="user_id",
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Review table definition"""

        db_table = "review"
        indexes = [
            models.Index(fields=["property_obj"], name="idx_review_property"),
            models.Index(fields=["user"], name="idx_review_user"),
        ]
        # Ensure one review per user per property
        unique_together = ["property_obj", "user"]

    def __str__(self):
        # pylint: disable=no-member
        return f"Review by {self.user.first_name} for {self.property_obj.name} - {self.rating} stars"
class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    payment_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    reference = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_method = models.CharField(max_length=50, default='chapa')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.reference} - {self.status}"

    class Meta:
        ordering = ['-created_at']