
from .views import RegistrationView, UsernameValidationView, EmailValidationView, VerficationView, LoginView, LogoutView , RequestPasswordResetEmail, CompletePasswordReset
from django.urls import path
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('register', RegistrationView.as_view(),  name='register'),
    path('login', csrf_exempt(LoginView.as_view()), name='login'),
    path('validate-username', csrf_exempt(UsernameValidationView.as_view()), name='validate_username'),
    path('validate-email', csrf_exempt(EmailValidationView.as_view()), name='validate_email'),
    path('activate/<uidb64>/<token>', csrf_exempt(VerficationView.as_view()), name='activate'),
    path('set-newpassword/<uidb64>/<token>', csrf_exempt(CompletePasswordReset.as_view()), name='reset-user-password'),
    path('logout', csrf_exempt(LogoutView.as_view()), name='logout'),
    path('request-password', csrf_exempt(RequestPasswordResetEmail.as_view()), name='request-password')
]