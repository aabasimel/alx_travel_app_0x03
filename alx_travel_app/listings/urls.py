"""Module import for listings.views"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views  
from .views import PropertyViewSet, BookingViewSet, UserViewSet, ReviewViewSet,ApproveAdminView,PaymentViewSet

router = DefaultRouter()
router.register(r"properties", PropertyViewSet, basename="property")
router.register(r"bookings", BookingViewSet, basename="booking")
router.register(r"reviews", ReviewViewSet, basename="review")
router.register(r"users", UserViewSet, basename="user")
router.register(r"payments", PaymentViewSet, basename="payment")

APP_NAME = "listings"

urlpatterns = [
    path("", include(router.urls)),  
    
    # Authentication
    path('auth/register/', views.UserRegistrationView.as_view(), name='register'),
    path('auth/login/', views.UserLoginView.as_view(), name='login'),
    path('auth/logout/', views.UserLogoutView.as_view(), name='logout'),
    
    # User profiles
    path('user/profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('user/stats/', views.UserStatsView.as_view(), name='user-stats'),
    
    # Search
    path('search/properties/', views.PropertySearchView.as_view(), name='property-search'),
    
    # Dashboards
    path('dashboard/host/', views.HostDashboardView.as_view(), name='host-dashboard'),
    path('users/<uuid:user_id>/approve-admin/', ApproveAdminView.as_view(), name='approve-admin'),

    

]