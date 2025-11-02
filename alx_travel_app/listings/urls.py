"""Module import for listings.views"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet, BookingViewSet, UserViewSet, ReviewViewSet

router = DefaultRouter()
router.register(r"properties", PropertyViewSet, basename="property")
router.register(r"bookings", BookingViewSet, basename="booking")
router.register(r"reviews", ReviewViewSet, basename="review")
router.register(r"users", UserViewSet, basename="user")

APP_NAME = "listings"

urlpatterns = [
    path("", include(router.urls)),
    path('api/', include(router.urls)),
    

    path('api/auth/', include('rest_framework.urls')),  
]