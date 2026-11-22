from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from cart.cart import Cart
from .models import Order, OrderItem, Payment
from products.models import Product
import uuid
import json
import os
from django.conf import settings

# Create your views here.

@login_required
def checkout(request):
    """Checkout page - Step 1: Review cart and enter shipping info"""
    cart = Cart(request)
    
    if len(cart) == 0:
        messages.error(request, 'Your cart is empty.')
        return redirect('products:product_list')
    
    if request.method == 'POST':
        # Save shipping info in session for next step
        request.session['shipping_info'] = {
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'email': request.POST.get('email'),
            'phone': request.POST.get('phone'),
            'address': request.POST.get('address'),
            'city': request.POST.get('city'),
            'postal_code': request.POST.get('postal_code'),
            'country': request.POST.get('country', 'Rwanda'),
            'notes': request.POST.get('notes', ''),
        }
        return redirect('orders:payment_method')
    
    context = {
        'cart': cart,
        'user': request.user,
    }
    return render(request, 'orders/checkout.html', context)

@login_required
def payment_method(request):
    """Step 2: Choose payment method"""
    cart = Cart(request)
    shipping_info = request.session.get('shipping_info')
    
    if not shipping_info:
        messages.error(request, 'Please complete shipping information first.')
        return redirect('orders:checkout')
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        request.session['payment_method'] = payment_method
        return redirect('orders:process_payment')
    
    # Calculate totals - FIXED: Use Decimal for all calculations
    subtotal = cart.get_total_price()  # This is already a Decimal
    
    # Convert all numbers to Decimal
    shipping_cost = Decimal('5.00') if subtotal < Decimal('50') else Decimal('0')
    tax = subtotal * Decimal('0.18')  # 18% VAT as Decimal
    total = subtotal + shipping_cost + tax
    
    context = {
        'cart': cart,
        'shipping_info': shipping_info,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'total': total,
    }
    return render(request, 'orders/payment_method.html', context)

@login_required
def process_payment(request):
    """Step 3: Process payment based on selected method"""
    cart = Cart(request)
    shipping_info = request.session.get('shipping_info')
    payment_method = request.session.get('payment_method')
    
    if not shipping_info or not payment_method:
        messages.error(request, 'Session expired. Please start over.')
        return redirect('orders:checkout')
    
    # Calculate totals for display
    subtotal = cart.get_total_price()
    shipping_cost = Decimal('5.00') if subtotal < Decimal('50') else Decimal('0')
    tax = subtotal * Decimal('0.18')
    total = subtotal + shipping_cost + tax
    
    if request.method == 'POST':
        # Handle different payment methods submission
        if payment_method == 'mtn_money':
            return process_mtn_money(request, cart, shipping_info)
        elif payment_method in ['visa', 'mastercard']:
            return process_card_payment(request, cart, shipping_info, payment_method)
        elif payment_method in ['bitcoin', 'ethereum']:
            return process_crypto_payment(request, cart, shipping_info, payment_method)
        elif payment_method == 'paypal':
            return process_paypal_payment(request, cart, shipping_info)
    
    # GET request - show payment form
    template_name = f'orders/payment_{payment_method}.html'
    
    # If specific template doesn't exist, use generic one
    template_path = os.path.join(settings.BASE_DIR, 'orders', 'templates', template_name)
    
    if not os.path.exists(template_path):
        if payment_method in ['visa', 'mastercard']:
            template_name = 'orders/payment_card.html'
        elif payment_method in ['bitcoin', 'ethereum']:
            template_name = 'orders/payment_crypto.html'
    
    # Convert Decimal to string for template to avoid JSON serialization issues
    context = {
        'payment_method': payment_method,
        'total': float(total),
        'subtotal': float(subtotal),
        'shipping_cost': float(shipping_cost),
        'tax': float(tax),
    }
    return render(request, template_name, context)

@login_required
@transaction.atomic
def process_mtn_money(request, cart, shipping_info):
    """Process MTN Money payment"""
    phone_number = request.POST.get('phone_number')
    
    # Validate phone number
    if not phone_number or len(phone_number) < 10:
        messages.error(request, 'Invalid phone number.')
        return redirect('orders:process_payment')
    
    # Create order
    order = create_order(request.user, cart, shipping_info, 'mtn_money')
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        payment_method='mtn_money',
        amount=order.total,
        status='completed',
        transaction_id=f"MTN-{uuid.uuid4().hex[:10].upper()}",
        phone_number=phone_number
    )
    
    # Clear cart and session
    cart.clear()
    if 'shipping_info' in request.session:
        del request.session['shipping_info']
    if 'payment_method' in request.session:
        del request.session['payment_method']
    
    messages.success(request, f'Payment successful! Your order #{order.order_number} has been placed.')
    return redirect('orders:order_confirmation', order_id=order.id)

@login_required
@transaction.atomic
def process_card_payment(request, cart, shipping_info, card_type):
    """Process Visa/Mastercard payment"""
    card_number = request.POST.get('card_number')
    card_holder = request.POST.get('card_holder')
    
    # Basic validation
    if not card_number or len(card_number) < 16:
        messages.error(request, 'Invalid card number.')
        return redirect('orders:process_payment')
    
    # Create order
    order = create_order(request.user, cart, shipping_info, card_type)
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        payment_method=card_type,
        amount=order.total,
        status='completed',
        transaction_id=f"CARD-{uuid.uuid4().hex[:10].upper()}",
        card_last4=card_number[-4:],
        card_brand=card_type
    )
    
    # Clear cart and session
    cart.clear()
    if 'shipping_info' in request.session:
        del request.session['shipping_info']
    if 'payment_method' in request.session:
        del request.session['payment_method']
    
    messages.success(request, f'Payment successful! Your order #{order.order_number} has been placed.')
    return redirect('orders:order_confirmation', order_id=order.id)

@login_required
@transaction.atomic
def process_crypto_payment(request, cart, shipping_info, crypto_type):
    """Process cryptocurrency payment"""
    wallet_address = request.POST.get('wallet_address')
    
    # Generate payment address
    payment_address = f"0x{uuid.uuid4().hex[:40].upper()}"
    
    # Create order
    order = create_order(request.user, cart, shipping_info, crypto_type)
    
    # Create payment record
    payment = Payment.objects.create(
        order=order,
        payment_method=crypto_type,
        amount=order.total,
        status='processing',
        transaction_id=f"CRYPTO-{uuid.uuid4().hex[:10].upper()}",
        crypto_address=payment_address,
        crypto_network=crypto_type
    )
    
    # Clear cart
    cart.clear()
    
    # Store payment info in session
    request.session['crypto_payment'] = {
        'order_id': order.id,
        'payment_address': payment_address,
        'amount': str(order.total),
        'crypto_type': crypto_type
    }
    
    return redirect('orders:crypto_payment_instructions', order_id=order.id)

@login_required
def crypto_payment_instructions(request, order_id):
    """Show cryptocurrency payment instructions"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    crypto_info = request.session.get('crypto_payment', {})
    
    context = {
        'order': order,
        'crypto_info': crypto_info,
    }
    return render(request, 'orders/crypto_instructions.html', context)

@login_required
def process_paypal_payment(request, cart, shipping_info):
    """Process PayPal payment - Create order and show PayPal form"""
    # Create order
    order = create_order(request.user, cart, shipping_info, 'paypal')
    
    # Calculate totals
    subtotal = cart.get_total_price()
    shipping_cost = Decimal('5.00') if subtotal < Decimal('50') else Decimal('0')
    tax = subtotal * Decimal('0.18')
    total = subtotal + shipping_cost + tax
    
    # Store order info in session (convert Decimal to string/float)
    request.session['pending_order_id'] = int(order.id)
    request.session['pending_order_total'] = float(total)
    request.session.modified = True
    
    context = {
        'payment_method': 'paypal',
        'total': float(total),
        'order_id': order.id,
    }
    return render(request, 'orders/payment_paypal.html', context)

def create_order(user, cart, shipping_info, payment_method):
    """Helper function to create order and order items - FIXED with Decimal"""
    
    # Calculate totals - use Decimal
    subtotal = cart.get_total_price()
    shipping_cost = Decimal('5.00') if subtotal < Decimal('50') else Decimal('0')
    tax = subtotal * Decimal('0.18')
    total = subtotal + shipping_cost + tax
    
    # Create order
    order = Order.objects.create(
        user=user,
        first_name=shipping_info['first_name'],
        last_name=shipping_info['last_name'],
        email=shipping_info['email'],
        phone=shipping_info['phone'],
        address=shipping_info['address'],
        city=shipping_info['city'],
        postal_code=shipping_info['postal_code'],
        country=shipping_info.get('country', 'Rwanda'),
        notes=shipping_info.get('notes', ''),
        payment_method=payment_method,
        subtotal=subtotal,
        shipping_cost=shipping_cost,
        tax=tax,
        total=total
    )
    
    # Create order items and update stock
    for item in cart:
        OrderItem.objects.create(
            order=order,
            product=item['product'],
            price=item['price'],
            quantity=item['quantity']
        )
        
        # Update product stock
        product = item['product']
        product.stock -= item['quantity']
        product.save()
    
    return order

@login_required
def order_history(request):
    """Display user's order history with estimated delivery"""
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product').order_by('-created')
    
    # Add estimated delivery date to each order (7 days from order date)
    for order in orders:
        order.estimated_delivery = order.created + timedelta(days=7)
    
    context = {
        'orders': orders,
    }
    return render(request, 'orders/order_history.html', context)

@login_required
def order_detail(request, order_id):
    """Display specific order details"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'orders/order_detail.html', context)

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page after successful payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'orders/order_confirmation.html', context)

@login_required
def paypal_return(request):
    """Handle PayPal return after successful payment"""
    order_id = request.session.get('pending_order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            order.payment_status = 'completed'
            order.status = 'processing'
            order.save()
            
            # Clear cart and session
            cart = Cart(request)
            cart.clear()
            
            # Clear session data
            if 'shipping_info' in request.session:
                del request.session['shipping_info']
            if 'payment_method' in request.session:
                del request.session['payment_method']
            if 'pending_order_id' in request.session:
                del request.session['pending_order_id']
            if 'pending_order_total' in request.session:
                del request.session['pending_order_total']
            
            messages.success(request, f'✅ Payment successful! Your order #{order.order_number} has been placed.')
            return redirect('orders:order_confirmation', order_id=order.id)
        except Order.DoesNotExist:
            pass
    
    messages.error(request, '❌ Payment verification failed. Please contact support.')
    return redirect('orders:checkout')

@login_required
def paypal_cancel(request):
    """Handle PayPal payment cancellation"""
    order_id = request.session.get('pending_order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            # Restore stock
            for item in order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
            order.delete()
        except Order.DoesNotExist:
            pass
    
    # Clear session data
    if 'pending_order_id' in request.session:
        del request.session['pending_order_id']
    if 'pending_order_total' in request.session:
        del request.session['pending_order_total']
    
    messages.warning(request, 'Payment was cancelled. You can try again.')
    return redirect('orders:payment_method')


@login_required
def track_order(request, order_id):
    """Track order status"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Calculate estimated delivery date
    estimated_delivery = order.created + timedelta(days=7)
    
    context = {
        'order': order,
        'estimated_delivery': estimated_delivery,
    }
    return render(request, 'orders/track_order.html', context)
@login_required
def cancel_order(request, order_id):
    """Cancel order if still pending"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status != 'pending':
        messages.error(request, 'Only pending orders can be cancelled.')
        return redirect('orders:order_detail', order_id=order.id)
    
    if request.method == 'POST':
        # Restore stock
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        
        order.status = 'cancelled'
        order.save()
        
        messages.success(request, f'Order #{order.order_number} has been cancelled.')
        return redirect('orders:order_history')
    
    context = {
        'order': order,
    }
    return render(request, 'orders/cancel_order.html', context)

# AJAX endpoints for payment processing
@login_required
def verify_mtn_payment(request):
    """AJAX endpoint to verify MTN payment status"""
    if request.method == 'POST':
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        
        return JsonResponse({
            'status': 'completed',
            'message': 'Payment verified successfully'
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def verify_crypto_payment(request):
    """AJAX endpoint to verify crypto payment"""
    if request.method == 'POST':
        data = json.loads(request.body)
        transaction_hash = data.get('transaction_hash')
        
        return JsonResponse({
            'status': 'confirmed',
            'confirmations': 3,
            'message': 'Transaction confirmed'
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def paypal_return(request):
    """Handle PayPal return after successful payment"""
    order_id = request.session.get('pending_order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            order.payment_status = 'completed'
            order.status = 'processing'
            order.save()
            
            # Clear cart
            cart = Cart(request)
            cart.clear()
            
            # Clear session
            if 'shipping_info' in request.session:
                del request.session['shipping_info']
            if 'payment_method' in request.session:
                del request.session['payment_method']
            if 'pending_order_id' in request.session:
                del request.session['pending_order_id']
            
            messages.success(request, f'✅ Payment successful! Your order #{order.order_number} has been placed.')
            return redirect('orders:order_confirmation', order_id=order.id)
        except Order.DoesNotExist:
            pass
    
    messages.error(request, '❌ Payment verification failed.')
    return redirect('orders:checkout')

@login_required
def paypal_cancel(request):
    """Handle PayPal payment cancellation"""
    order_id = request.session.get('pending_order_id')
    
    if order_id:
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            # Restore stock
            for item in order.items.all():
                product = item.product
                product.stock += item.quantity
                product.save()
            order.delete()
        except Order.DoesNotExist:
            pass
    
    # Clear session
    if 'pending_order_id' in request.session:
        del request.session['pending_order_id']
    
    messages.warning(request, 'Payment was cancelled. You can try again.')
    return redirect('orders:payment_method')

@login_required
def order_confirmation(request, order_id):
    """Order confirmation page after successful payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    estimated_delivery = order.created + timedelta(days=7)
    
    context = {
        'order': order,
        'estimated_delivery': estimated_delivery,
    }
    return render(request, 'orders/order_confirmation.html', context)