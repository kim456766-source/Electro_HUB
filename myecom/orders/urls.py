from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    # Checkout flow
    path('checkout/', views.checkout, name='checkout'),
    path('payment-method/', views.payment_method, name='payment_method'),
    path('process-payment/', views.process_payment, name='process_payment'),
    
    # PayPal payment processing
    path('paypal-return/', views.paypal_return, name='paypal_return'),
    path('paypal-cancel/', views.paypal_cancel, name='paypal_cancel'),
    
    # Payment processing
    path('mtn-money/', views.process_mtn_money, name='process_mtn_money'),
    path('crypto-instructions/<int:order_id>/', views.crypto_payment_instructions, name='crypto_payment_instructions'),
    
    # Order management
    path('history/', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('track/<int:order_id>/', views.track_order, name='track_order'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    
    # AJAX endpoints
    path('verify-mtn/', views.verify_mtn_payment, name='verify_mtn_payment'),
    path('verify-crypto/', views.verify_crypto_payment, name='verify_crypto_payment'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    path('track/<int:order_id>/', views.track_order, name='track_order'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
]