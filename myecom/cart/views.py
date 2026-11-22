from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from products.models import Product
from .cart import Cart

def cart_detail(request):
    """Display shopping cart."""
    cart = Cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})

@require_POST
def cart_add(request, product_id):
    """Add a product to cart with AJAX support"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id, available=True)
    quantity = int(request.POST.get('quantity', 1))
    
    # Check if enough stock
    if quantity > product.stock:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f'Sorry, only {product.stock} items available.'
            }, status=400)
        messages.error(request, f'Sorry, only {product.stock} items available.')
        return redirect('products:product_detail', product_slug=product.slug)
    
    # Add to cart
    cart.add(product=product, quantity=quantity)
    
    # Get updated cart count
    cart_count = len(cart)
    cart_total = cart.get_total_price()
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': f'{quantity} x {product.name} added to cart!',
            'cart_count': cart_count,
            'cart_total': str(cart_total),
            'product_name': product.name,
            'quantity': quantity
        })
    
    messages.success(request, f'{quantity} x {product.name} added to your cart!')
    
    if 'checkout' in request.POST:
        return redirect('cart:cart_detail')
    return redirect('products:product_detail', product_slug=product.slug)

def cart_remove(request, product_id):
    """Remove a product from cart"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_count': len(cart),
            'cart_total': str(cart.get_total_price())
        })
    
    messages.success(request, f'{product.name} removed from cart.')
    return redirect('cart:cart_detail')

def cart_update(request, product_id):
    """Update quantity of a product in cart"""
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > product.stock:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': f'Sorry, only {product.stock} items available.'
            }, status=400)
        messages.error(request, f'Sorry, only {product.stock} items available.')
    elif quantity > 0:
        cart.add(product=product, quantity=quantity, override_quantity=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'cart_count': len(cart),
                'cart_total': str(cart.get_total_price()),
                'item_total': str(cart.get_total_price())
            })
        messages.success(request, f'{product.name} quantity updated.')
    else:
        cart.remove(product)
    
    return redirect('cart:cart_detail')