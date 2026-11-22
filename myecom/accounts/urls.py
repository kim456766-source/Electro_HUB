from django.urls import path
from . import views

app_name = 'accounts'  # ✅ This must be here for namespace to work

urlpatterns = [
    path('register/', views.register_customer, name='register'),
    path('register/customer/', views.register_customer, name='register_customer'),
    path('register/seller/', views.register_seller, name='register_seller'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('password/change/', views.password_change_view, name='password_change'),
    
    # OTP-based password reset
    path('password-reset-otp/', views.password_reset_otp_request, name='password_reset_otp_request'),
    path('password-reset-otp/send/', views.password_reset_otp_send_api, name='password_reset_otp_send_api'),
    path('password-reset-otp/verify/', views.password_reset_otp_verify, name='password_reset_otp_verify'),
    path('password-reset-otp/set/', views.password_reset_otp_set, name='password_reset_otp_set'),
    path('password-reset-otp/resend/', views.password_reset_otp_resend, name='password_reset_otp_resend'),
    
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.wishlist_add, name='wishlist_add'),
    path('wishlist/remove/<int:product_id>/', views.wishlist_remove, name='wishlist_remove'),
    path('verify-email/', views.verify_email_done, name='verify_email_done'),
    path('verify-email/<uidb64>/<token>/', views.verify_email_confirm, name='verify_email_confirm'),
    path('verify-email/complete/', views.verify_email_complete, name='verify_email_complete'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    path('settings/', views.account_settings, name='settings'),
    path('delete-account/', views.delete_account, name='delete_account'),
    path('login-history/', views.login_history_view, name='login_history'),
    path('delete-account/', views.delete_account, name='delete_account'),
]