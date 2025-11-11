# tests/test_views.py
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Property, Booking, Review, Payment
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class BaseTestCase(APITestCase):
    def setUp(self):
        # Create test users
        self.guest_user = User.objects.create_user(
            email='guest@example.com',
            password='testpass123',
            first_name='Guest',
            last_name='User',
            role='guest'
        )
        
        self.host_user = User.objects.create_user(
            email='host@example.com',
            password='testpass123',
            first_name='Host',
            last_name='User',
            role='host'
        )
        
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        
        # Create test property
        self.property = Property.objects.create(
            host=self.host_user,
            name='Test Property',
            description='Beautiful test property',
            address='123 Test St',
            pricepernight=100.00,
            bedrooms=2,
            bathrooms=1,
            max_guests=4
        )
        
        # Create test booking
        self.booking = Booking.objects.create(
            user=self.guest_user,
            property_obj=self.property,
            start_date=timezone.now().date() + timedelta(days=7),
            end_date=timezone.now().date() + timedelta(days=10),
            total_price=300.00,
            status='pending'
        )
        
        # Create test review
        self.review = Review.objects.create(
            user=self.guest_user,
            property_obj=self.property,
            rating=5,
            comment='Excellent property!'
        )
        
        # Create test payment
        self.payment = Payment.objects.create(
            booking=self.booking,
            amount=300.00,
            reference='TEST_REF_001',
            status='pending'
        )
        
        # Setup clients
        self.client = APIClient()


class AuthenticationTests(BaseTestCase):
    def test_user_registration(self):
        """Test user registration"""
        url = reverse('user-registration')
        data = {
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'guest'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email='newuser@example.com').exists())