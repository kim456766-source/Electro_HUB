from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.sites.shortcuts import get_current_site
from django.utils import timezone
from .tokens import account_activation_token
import random
import string

def send_verification_email(request, user):
    """
    Send email verification link to user
    """
    token = account_activation_token.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    
    # Build verification URL
    verification_url = reverse('accounts:verify_email_confirm', kwargs={
        'uidb64': uid,
        'token': token
    })
    
    current_site = get_current_site(request)
    verification_link = f"http://{current_site.domain}{verification_url}"
    
    # Email subject and message
    subject = 'Verify your email address'
    message = f"""
    Hi {user.username},
    
    Please click the link below to verify your email address:
    {verification_link}
    
    This link will expire in 24 hours.
    
    If you didn't create an account, please ignore this email.
    
    Thanks,
    MyEcom Team
    """
    
    # Send email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )

def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_otp_code():
    """Generate a 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=6))


def send_otp_email(user, code):
    """
    Send OTP code to user's email for password reset
    """
    subject = 'Password Reset OTP - MyEcom'
    message = f"""
    Hi {user.username},

    Your password reset OTP code is: {code}

    This code will expire in 10 minutes.

    If you didn't request a password reset, please ignore this email.

    Thanks,
    MyEcom Team
    """

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def create_password_reset_otp(user):
    """
    Create a new OTP code for password reset
    """
    from .models import PasswordResetCode
    
    # Invalidate any existing unused codes for this user
    PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)
    
    # Generate new code
    code = generate_otp_code()
    
    # Set expiration time (10 minutes)
    expires_at = timezone.now() + timezone.timedelta(minutes=10)
    
    # Create and save the code
    reset_code = PasswordResetCode.objects.create(
        user=user,
        code=code,
        expires_at=expires_at
    )
    
    # Send the code via email
    send_otp_email(user, code)
    
    return reset_code