from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient,APITestCase
from unittest.mock import patch,MagicMock
from decimal import Decimal
from datetime import date,timedelta
from models import User,Property,Booking,Review


class PropertyBookingPaymentTests(APITestCase):
    def setUp(self):
        self.client=APIClient()
        self.host=User.create_user(
            email="host@gmail.com",
            password="123",
            first_name="Host",
            last_name="Host",
            role="host"

        )
        self.guest=User.create_user(
            email="guest@gmail.com",
            password="123",
            first_name="Guest",
            last_name="Guest",
            role="guest"
        )
        self.client.force_authenticate(user=self.guest)

        self.property=Property.objects.create(
            host=self.host,
            name="Test Propery",
            description="Nice place",
            location="Test city",
            pricepernight=Decimal("100.00")
        )