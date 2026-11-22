
from django.db import models
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q, Avg, Min, Max
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Product, Category, ProductReview, ProductSpecification
from accounts.models import Wishlist
from cart.cart import Cart
from django.contrib.admin.views.decorators import staff_member_required
from .models import Product, Category
from orders.models import Order
from accounts.models import User
from .decorators import admin_required
from django.db.models import Count, Sum, Q
from decimal import Decimal
from django.shortcuts import render
import json
from django.utils.text import slugify
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
from django.contrib.auth.hashers import make_password
from accounts.models import Profile
from .models import Seller, SellerProduct, Category
from django.db import transaction
from django.utils.text import slugify
from accounts.models import User, SellerProfile



def home(request):
    """Home page with featured products and categories"""
    # Get featured products (limit to 8)
    featured_products = Product.objects.filter(
        featured=True, 
        available=True
    ).select_related('category').annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    )[:8]
    
    # Get new arrivals (latest 4 products)
    new_arrivals = Product.objects.filter(
        available=True
    ).select_related('category').annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ).order_by('-created')[:4]
    
    # Get all categories with product counts
    categories_list = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__available=True))
    ).all()
    
    # Add pagination for categories
    page = request.GET.get('category_page', 1)
    paginator = Paginator(categories_list, 8)
    
    try:
        categories = paginator.page(page)
    except PageNotAnInteger:
        categories = paginator.page(1)
    except EmptyPage:
        categories = paginator.page(paginator.num_pages)
    
    # Get top rated products (if you have reviews)
    top_rated = Product.objects.filter(
        available=True,
        reviews__isnull=False
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    ).order_by('-avg_rating')[:4]
    
    # Get wishlist count for authenticated users
    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
    
    # Get deals count (products on sale)
    deals_count = Product.objects.filter(
        available=True,
        on_sale=True
    ).count()
    
    context = {
        'featured_products': featured_products,
        'new_arrivals': new_arrivals,
        'categories': categories,
        'top_rated': top_rated,
        'wishlist_count': wishlist_count,
        'deals_count': deals_count,
    }
    return render(request, 'products/home.html', context)

def product_list(request, category_slug=None):
    """
    Display products with filtering, sorting, and pagination
    Can filter by category if category_slug is provided
    """
    # Get all categories with product counts for sidebar
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__available=True))
    ).all()
    
    # Base queryset - only available products with related category and review stats
    products = Product.objects.filter(
        available=True
    ).select_related('category').annotate(
        avg_rating=Avg('reviews__rating'),
        reviews_count=Count('reviews')
    )
    
    # Filter by category if slug is provided
    category = None
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)
        
        # Get category stats
        category_stats = products.aggregate(
            min_price=Min('price'),
            max_price=Max('price'),
            avg_rating=Avg('reviews__rating'),
            total_reviews=Count('reviews')
        )
    else:
        category_stats = None
    
    # Apply filters from request GET parameters
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Sale items filter
    if request.GET.get('sale') == 'true':
        products = products.filter(on_sale=True)
    
    # In stock filter
    if request.GET.get('in_stock') == 'true':
        products = products.filter(stock__gt=0)
    
    # Rating filter
    min_rating = request.GET.get('min_rating')
    if min_rating:
        products = products.filter(avg_rating__gte=min_rating)
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'rating':
        products = products.order_by('-avg_rating', '-created')
    else:  # newest
        products = products.order_by('-created')
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 12)
    
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)
    
    # Get total products count for "All Products" link
    total_products = Product.objects.filter(available=True).count()
    
    # Get price range for filtering
    price_range = Product.objects.filter(available=True).aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    context = {
        'category': category,
        'categories': categories,
        'products': products,
        'total_products': total_products,
        'current_sort': sort_by,
        'category_stats': category_stats,
        'price_range': price_range,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'products/product_list.html', context)
def product_detail(request, product_slug):
    """Display product details and related products"""
    from django.db.models import Avg, Q
    
    product = get_object_or_404(Product, slug=product_slug, available=True)
    
    # Get product images
    product_images = [product.image] if product.image else []
    if product.image_2:
        product_images.append(product.image_2)
    if product.image_3:
        product_images.append(product.image_3)
    
    # Get specifications
    specifications = product.specifications.all()
    
    # Get reviews
    reviews = product.reviews.all()
    reviews_count = reviews.count()
    
    # Calculate average rating
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Calculate rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()
    
    # Check if user has reviewed
    user_review = None
    in_wishlist = False
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        in_wishlist = Wishlist.objects.filter(user=request.user, product=product).exists()
    
    # ========== RELATED PRODUCTS ==========
    # Get related products from same category (excluding current product)
    related_products = Product.objects.filter(
        category=product.category,
        available=True,
        is_approved=True
    ).exclude(id=product.id)[:8]
    
    # If not enough products from same category (less than 4), get popular products from other categories
    if related_products.count() < 4:
        additional_products = Product.objects.filter(
            available=True,
            is_approved=True
        ).exclude(id=product.id).exclude(category=product.category)[:8 - related_products.count()]
        related_products = list(related_products) + list(additional_products)
    
    # If still no products, get any available products
    if len(related_products) == 0:
        related_products = Product.objects.filter(
            available=True,
            is_approved=True
        ).exclude(id=product.id)[:8]
    
    context = {
        'product': product,
        'product_images': product_images,
        'specifications': specifications,
        'reviews': reviews,
        'reviews_count': reviews_count,
        'avg_rating': avg_rating,
        'rating_distribution': rating_distribution,
        'user_review': user_review,
        'in_wishlist': in_wishlist,
        'related_products': related_products,  # Make sure this is passed
    }
    
    return render(request, 'products/product_detail.html', context)

@login_required
def add_review(request, product_id):
    """Add or update a product review"""
    product = get_object_or_404(Product, id=product_id, available=True)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if rating and comment:
            review, created = ProductReview.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating': rating,
                    'comment': comment
                }
            )
            
            if created:
                messages.success(request, '✅ Your review has been added successfully!')
            else:
                messages.success(request, '✅ Your review has been updated successfully!')
        else:
            messages.error(request, '❌ Please provide both rating and comment.')
    
    return redirect('products:product_detail', product_slug=product.slug)

@login_required
def delete_review(request, review_id):
    """Delete a product review - only the author can delete their own review"""
    review = get_object_or_404(ProductReview, id=review_id)
    
    # Check if the logged-in user is the author of the review
    if review.user != request.user:
        messages.error(request, '❌ You cannot delete someone else\'s review.')
        return redirect('products:product_detail', product_slug=review.product.slug)
    
    product_slug = review.product.slug
    review.delete()
    messages.success(request, '✅ Your review has been deleted successfully!')
    return redirect('products:product_detail', product_slug=product_slug)

@login_required
def add_to_wishlist(request, product_id):
    """Add product to wishlist"""
    product = get_object_or_404(Product, id=product_id, available=True)
    
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        product=product
    )
    
    if created:
        messages.success(request, f'❤️ {product.name} added to wishlist!')
    else:
        wishlist_item.delete()
        messages.success(request, f'💔 {product.name} removed from wishlist!')
    
    return redirect(request.META.get('HTTP_REFERER', 'products:product_detail'))

def add_to_cart_from_detail(request, product_id):
    """Add product to cart with specified quantity"""
    if request.method == 'POST':
        cart = Cart(request)
        product = get_object_or_404(Product, id=product_id, available=True)
        
        quantity = int(request.POST.get('quantity', 1))
        
        # Check if enough stock
        if quantity > product.stock:
            messages.error(request, f'Sorry, only {product.stock} items available.')
            return redirect('products:product_detail', product_slug=product.slug)
        
        # Add to cart
        cart.add(product=product, quantity=quantity)
        
        messages.success(request, f'🛒 {quantity} x {product.name} added to your cart!')
        
        # Check if user wants to go to cart or continue shopping
        if 'checkout' in request.POST:
            return redirect('cart:cart_detail')
        else:
            return redirect('products:product_detail', product_slug=product.slug)
    
    return redirect('products:product_list')

def search_products(request):
    """Search products - redirects if single result found"""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return redirect('products:product_list')
    
    # Search for products
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query),
        available=True
    ).select_related('category')
    
    # Search for categories
    categories = Category.objects.filter(
        name__icontains=query
    )
    
    total_results = products.count() + categories.count()
    
    # If exact match found, redirect to that product
    exact_product = products.filter(name__iexact=query).first()
    if exact_product:
        return redirect('products:product_detail', slug=exact_product.slug)
    
    # If exact category match found, redirect to that category
    exact_category = categories.filter(name__iexact=query).first()
    if exact_category:
        return redirect('products:product_list_by_category', category_slug=exact_category.slug)
    
    # If only one product found, redirect directly to it
    if products.count() == 1 and categories.count() == 0:
        return redirect('products:product_detail', slug=products.first().slug)
    
    # If only one category found, redirect directly to it
    if categories.count() == 1 and products.count() == 0:
        return redirect('products:product_list_by_category', category_slug=categories.first().slug)
    
    # Multiple results - show search results page
    # Check if AJAX request for live search
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # Return JSON for live search
        products_data = []
        for product in products[:10]:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'slug': product.slug,
                'price': str(product.get_price()),
                'image_url': product.image.url if product.image else None,
                'category': product.category.name if product.category else '',
            })
        
        categories_data = []
        for category in categories[:5]:
            categories_data.append({
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'product_count': category.products.filter(available=True).count(),
            })
        
        return JsonResponse({
            'products': products_data,
            'categories': categories_data,
            'query': query,
            'total_results': total_results,
            'has_single_result': False,
        })
    
    # Regular request - show search results page
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    context = {
        'products': products_page,
        'categories': categories,
        'query': query,
        'results_count': total_results,
    }
    return render(request, 'products/search_results.html', context)
def live_search_suggestions(request):
    """API endpoint for live search suggestions"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    # Get product suggestions
    products = Product.objects.filter(
        Q(name__icontains=query) | 
        Q(description__icontains=query),
        available=True
    ).values_list('name', flat=True)[:5]
    
    # Get category suggestions
    categories = Category.objects.filter(
        name__icontains=query
    ).values_list('name', flat=True)[:3]
    
    suggestions = list(products) + list(categories)
    
    return JsonResponse({'suggestions': suggestions})
def filter_products_ajax(request):
    """
    AJAX endpoint for filtering products without page reload
    """
    products = Product.objects.filter(available=True).select_related('category')
    
    # Apply filters
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    min_price = request.GET.get('min_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    
    max_price = request.GET.get('max_price')
    if max_price:
        products = products.filter(price__lte=max_price)
    
    on_sale = request.GET.get('on_sale')
    if on_sale == 'true':
        products = products.filter(on_sale=True)
    
    in_stock = request.GET.get('in_stock')
    if in_stock == 'true':
        products = products.filter(stock__gt=0)
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')
    else:
        products = products.order_by('-created')
    
    # Prepare JSON response
    data = {
        'products': [
            {
                'id': p.id,
                'name': p.name,
                'price': str(p.price),
                'sale_price': str(p.sale_price) if p.sale_price else None,
                'on_sale': p.on_sale,
                'image_url': p.image.url if p.image else None,
                'slug': p.slug,
                'category': p.category.name,
            }
            for p in products[:20]
        ],
        'count': products.count(),
    }
    
    return JsonResponse(data)

def about(request):
    """About us page"""
    return render(request, 'products/about.html')

def contact(request):
    """Contact page with form submission"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Here you can send an email or save to database
        messages.success(request, f'Thank you {name}! Your message has been sent. We\'ll get back to you soon.')
        return redirect('products:contact')
    
    return render(request, 'products/contact.html')

def faq(request):
    """Frequently asked questions page"""
    return render(request, 'products/faq.html')

def deals(request):
    """Deals and offers page - show products on sale with countdown timers"""
    
    # Get base queryset of products on sale
    deals_queryset = Product.objects.filter(
        available=True, 
        on_sale=True
    ).select_related('category')
    
    # Calculate discount percentage for each product and add as attribute
    for product in deals_queryset:
        if product.price and product.sale_price and product.price > 0:
            discount = ((product.price - product.sale_price) / product.price) * 100
            product.discount_percentage = round(discount)
        else:
            product.discount_percentage = 0
    
    # Apply category filter if provided
    category_id = request.GET.get('category')
    if category_id:
        deals_queryset = deals_queryset.filter(category_id=category_id)
    
    # Calculate max discount from the queryset
    max_discount = 0
    for product in deals_queryset:
        if hasattr(product, 'discount_percentage') and product.discount_percentage > max_discount:
            max_discount = product.discount_percentage
    
    # Get total count of products on sale
    total_products_on_sale = deals_queryset.count()
    
    # Get categories with sale products count (for sidebar filter)
    categories = Category.objects.filter(
        products__on_sale=True,
        products__available=True
    ).annotate(
        sale_count=Count('products', filter=Q(products__on_sale=True, products__available=True))
    ).distinct()
    
    # Get ALL categories for footer navigation
    all_categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__available=True))
    ).all()[:6]
    
    # Order the deals by discount percentage (highest first)
    deals_list = list(deals_queryset)
    deals_list.sort(key=lambda x: x.discount_percentage if hasattr(x, 'discount_percentage') else 0, reverse=True)
    
    # Pagination
    paginator = Paginator(deals_list, 12)
    page = request.GET.get('page', 1)
    
    try:
        deals = paginator.page(page)
    except PageNotAnInteger:
        deals = paginator.page(1)
    except EmptyPage:
        deals = paginator.page(paginator.num_pages)
    
    context = {
        'deals': deals,
        'deals_count': total_products_on_sale,
        'categories': categories,
        'all_categories': all_categories,
        'max_discount': max_discount,
        'total_products_on_sale': total_products_on_sale,
    }
    return render(request, 'products/deals.html', context)

@staff_member_required
def admin_dashboard(request):
    """Admin Dashboard - Statistics and overview"""
    
    today = timezone.now().date()
    
    # Statistics
    total_products = Product.objects.count()
    total_categories = Category.objects.count()
    total_orders = Order.objects.count()
    total_users = User.objects.count()
    
    # Revenue stats
    revenue_result = Order.objects.filter(payment_status='completed').aggregate(total=Sum('total'))
    total_revenue = revenue_result['total'] or 0
    if isinstance(total_revenue, Decimal):
        total_revenue = float(total_revenue)
    
    # Orders by status
    pending_orders = Order.objects.filter(status='pending').count()
    processing_orders = Order.objects.filter(status='processing').count()
    shipped_orders = Order.objects.filter(status='shipped').count()
    delivered_orders = Order.objects.filter(status='delivered').count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    
    # Recent orders
    recent_orders = Order.objects.all().order_by('-created')[:10]
    
    # Low stock products
    low_stock_products = Product.objects.filter(stock__lt=10, available=True)[:10]
    
    # Popular products
    popular_products = Product.objects.annotate(
        order_count=Count('order_items')
    ).order_by('-order_count')[:5]
    
    # Recent users
    recent_users = User.objects.all().order_by('-date_joined')[:5]
    
    # Weekly sales data
    week_labels = []
    week_values = []
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        daily_result = Order.objects.filter(
            created__date=date,
            payment_status='completed'
        ).aggregate(total=Sum('total'))
        
        daily_total = daily_result['total'] or 0
        if isinstance(daily_total, Decimal):
            daily_total = float(daily_total)
        
        week_labels.append(date.strftime('%a'))
        week_values.append(daily_total)
    
    context = {
        'total_products': total_products,
        'total_categories': total_categories,
        'total_orders': total_orders,
        'total_users': total_users,
        'total_revenue': total_revenue,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'cancelled_orders': cancelled_orders,
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'popular_products': popular_products,
        'recent_users': recent_users,
        'week_labels': week_labels,
        'week_values': week_values,
    }
    return render(request, 'products/admin/dashboard.html', context)

@staff_member_required
def admin_products(request):
    """Admin Products Management"""
    products = Product.objects.all().select_related('category').order_by('-created')
    
    # Search
    search = request.GET.get('search')
    if search:
        products = products.filter(name__icontains=search)
    
    context = {
        'products': products,
    }
    return render(request, 'products/admin/products.html', context)

@staff_member_required
def admin_orders(request):
    """Admin Orders Management"""
    orders = Order.objects.all().order_by('-created')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    context = {
        'orders': orders,
    }
    return render(request, 'products/admin/orders.html', context)

@staff_member_required
def admin_users(request):
    """Admin Users Management"""
    users = User.objects.all().order_by('-date_joined')
    
    # Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(email__icontains=search)
        )
    
    context = {
        'users': users,
    }
    return render(request, 'products/admin/users.html', context)

@staff_member_required
def admin_categories(request):
    """Admin Categories Management"""
    categories = Category.objects.all().annotate(
        product_count=Count('products')
    ).order_by('name')
    
    context = {
        'categories': categories,
    }
    return render(request, 'products/admin/categories.html', context)

@staff_member_required
def admin_add_product(request):
    """Add new product - Custom admin page"""
    
    if request.method == 'POST':
        try:
            # Get basic product data
            name = request.POST.get('name')
            category_id = request.POST.get('category')
            slug = request.POST.get('slug')
            description = request.POST.get('description')
            price = request.POST.get('price')
            sale_price = request.POST.get('sale_price') or None
            stock = request.POST.get('stock')
            on_sale = request.POST.get('on_sale') == 'on'
            featured = request.POST.get('featured') == 'on'
            available = request.POST.get('available') == 'on'
            
            # Create slug if not provided
            if not slug:
                slug = slugify(name)
                # Ensure unique slug
                original_slug = slug
                counter = 1
                while Product.objects.filter(slug=slug).exists():
                    slug = f"{original_slug}-{counter}"
                    counter += 1
            
            # Get category
            category = get_object_or_404(Category, id=category_id)
            
            # Create product
            product = Product.objects.create(
                category=category,
                name=name,
                slug=slug,
                description=description,
                price=price,
                sale_price=sale_price if sale_price else None,
                stock=stock,
                on_sale=on_sale,
                featured=featured,
                available=available
            )
            
            # Handle main image
            if request.FILES.get('main_image'):
                product.image = request.FILES['main_image']
            
            # Handle additional images
            if request.FILES.get('image_2'):
                product.image_2 = request.FILES['image_2']
            if request.FILES.get('image_3'):
                product.image_3 = request.FILES['image_3']
            if request.FILES.get('image_4'):
                # If you have image_4 field in model
                product.image_4 = request.FILES['image_4']
            
            product.save()
            
            # Handle specifications
            for key, value in request.POST.items():
                if key.startswith('spec_name_'):
                    index = key.split('_')[-1]
                    spec_name = value
                    spec_value = request.POST.get(f'spec_value_{index}')
                    if spec_name and spec_value:
                        ProductSpecification.objects.create(
                            product=product,
                            name=spec_name,
                            value=spec_value
                        )
            
            messages.success(request, f'Product "{name}" created successfully!')
            
            # Redirect based on button clicked
            if request.POST.get('action') == 'save_and_add':
                return redirect('products:admin_add_product')
            else:
                return redirect('products:admin_products')
            
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
    
    # Get categories for dropdown
    categories = Category.objects.all()
    
    context = {
        'categories': categories,
    }
    return render(request, 'products/admin/add_product.html', context)

@staff_member_required
def admin_add_category(request):
    """Add new category - Custom admin page"""
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name')
            slug = request.POST.get('slug')
            description = request.POST.get('description')
            show_in_menu = request.POST.get('show_in_menu') == 'on'
            
            # Create slug if not provided
            if not slug:
                slug = slugify(name)
                # Ensure unique slug
                original_slug = slug
                counter = 1
                while Category.objects.filter(slug=slug).exists():
                    slug = f"{original_slug}-{counter}"
                    counter += 1
            
            # Create category
            category = Category.objects.create(
                name=name,
                slug=slug,
                description=description,
                show_in_menu=show_in_menu
            )
            
            # Handle image upload
            if request.FILES.get('image'):
                category.image = request.FILES['image']
                category.save()
            
            messages.success(request, f'Category "{name}" created successfully!')
            
            if request.POST.get('action') == 'save_and_add':
                return redirect('products:admin_add_category')
            else:
                return redirect('products:admin_categories')
                
        except Exception as e:
            messages.error(request, f'Error creating category: {str(e)}')
    
    context = {}
    return render(request, 'products/admin/add_category.html', context)

@staff_member_required
def admin_edit_category(request, category_id):
    """Edit existing category"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        try:
            category.name = request.POST.get('name')
            category.slug = request.POST.get('slug')
            category.description = request.POST.get('description')
            category.show_in_menu = request.POST.get('show_in_menu') == 'on'
            
            # Handle image
            if request.POST.get('remove_image') == '1':
                if category.image:
                    category.image.delete()
                    category.image = None
            elif request.FILES.get('image'):
                if category.image:
                    category.image.delete()
                category.image = request.FILES['image']
            
            category.save()
            
            messages.success(request, f'Category "{category.name}" updated successfully!')
            return redirect('products:admin_categories')
            
        except Exception as e:
            messages.error(request, f'Error updating category: {str(e)}')
    
    context = {'category': category}
    return render(request, 'products/admin/edit_category.html', context)

@staff_member_required
def admin_delete_category(request, category_id):
    """Delete category"""
    category = get_object_or_404(Category, id=category_id)
    category_name = category.name
    category.delete()
    
    messages.success(request, f'Category "{category_name}" has been deleted.')
    return redirect('products:admin_categories')

@staff_member_required
def admin_edit_product(request, product_id):
    """Edit existing product"""
    product = get_object_or_404(Product, id=product_id)
    categories = Category.objects.all()
    
    if request.method == 'POST':
        try:
            product.name = request.POST.get('name')
            product.category_id = request.POST.get('category')
            product.description = request.POST.get('description')
            product.price = request.POST.get('price')
            product.sale_price = request.POST.get('sale_price') or None
            product.stock = request.POST.get('stock')
            product.on_sale = request.POST.get('on_sale') == 'on'
            product.featured = request.POST.get('featured') == 'on'
            product.available = request.POST.get('available') == 'on'
            product.save()
            
            messages.success(request, f'Product "{product.name}" updated successfully!')
            return redirect('products:admin_products')
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
    
    context = {
        'product': product,
        'categories': categories,
    }
    return render(request, 'products/admin/edit_product.html', context)

@staff_member_required
def admin_delete_product(request, product_id):
    """Delete product"""
    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    product.delete()
    
    messages.success(request, f'Product "{product_name}" has been deleted.')
    return redirect('products:admin_products')

@staff_member_required
def admin_update_order_status(request, order_id):
    """Update order status from admin panel"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        order.status = new_status
        order.save()
        messages.success(request, f'Order #{order.order_number} status updated to {order.get_status_display()}')
    
    return redirect('products:admin_orders')

@staff_member_required
def admin_users(request):
    """Admin Users Management - List all users"""
    users = User.objects.all().order_by('-date_joined')
    
    # Search
    search = request.GET.get('search')
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    # Filter by role
    role = request.GET.get('role')
    if role == 'admin':
        users = users.filter(is_staff=True)
    elif role == 'customer':
        users = users.filter(is_staff=False, is_superuser=False)
    
    context = {
        'users': users,
    }
    return render(request, 'products/admin/users.html', context)

@staff_member_required
def admin_add_user(request):
    """Add new user - Custom admin page (No Django admin)"""
    
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            first_name = request.POST.get('first_name', '')
            last_name = request.POST.get('last_name', '')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            is_active = request.POST.get('is_active') == 'on'
            is_staff = request.POST.get('is_staff') == 'on'
            is_superuser = request.POST.get('is_superuser') == 'on'
            phone = request.POST.get('phone', '')
            address = request.POST.get('address', '')
            city = request.POST.get('city', '')
            country = request.POST.get('country', 'Rwanda')
            newsletter = request.POST.get('newsletter') == 'on'
            
            # Validation
            if not username or not email or not password1:
                messages.error(request, 'Username, email and password are required.')
                return redirect('products:admin_add_user')
            
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('products:admin_add_user')
            
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists.')
                return redirect('products:admin_add_user')
            
            if password1 != password2:
                messages.error(request, 'Passwords do not match.')
                return redirect('products:admin_add_user')
            
            if len(password1) < 8:
                messages.error(request, 'Password must be at least 8 characters.')
                return redirect('products:admin_add_user')
            
            # Create user
            user = User.objects.create(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=is_active,
                is_staff=is_staff,
                is_superuser=is_superuser
            )
            user.set_password(password1)
            user.save()
            
            # Create or update profile
            profile, created = Profile.objects.get_or_create(user=user)
            profile.phone = phone
            profile.address = address
            profile.city = city
            profile.country = country
            profile.newsletter_subscribed = newsletter
            
            # Handle avatar
            if request.FILES.get('avatar'):
                profile.profile_picture = request.FILES['avatar']
            
            profile.save()
            
            messages.success(request, f'User "{username}" created successfully!')
            
            if request.POST.get('action') == 'save_and_add':
                return redirect('products:admin_add_user')
            else:
                return redirect('products:admin_users')
                
        except Exception as e:
            messages.error(request, f'Error creating user: {str(e)}')
            return redirect('products:admin_add_user')
    
    return render(request, 'products/admin/add_user.html')

@staff_member_required
def admin_edit_user(request, user_id):
    """Edit existing user - Custom admin page (No Django admin)"""
    user = get_object_or_404(User, id=user_id)
    
    try:
        profile = user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=user)
    
    if request.method == 'POST':
        try:
            user.username = request.POST.get('username')
            user.email = request.POST.get('email')
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.is_active = request.POST.get('is_active') == 'on'
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.is_superuser = request.POST.get('is_superuser') == 'on'
            
            # Check if username exists for other users
            if User.objects.exclude(id=user_id).filter(username=user.username).exists():
                messages.error(request, 'Username already exists.')
                return redirect('products:admin_edit_user', user_id=user_id)
            
            # Change password if provided
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            if password1 and password2:
                if password1 == password2:
                    if len(password1) >= 8:
                        user.set_password(password1)
                    else:
                        messages.error(request, 'Password must be at least 8 characters.')
                        return redirect('products:admin_edit_user', user_id=user_id)
                else:
                    messages.error(request, 'Passwords do not match.')
                    return redirect('products:admin_edit_user', user_id=user_id)
            
            user.save()
            
            # Update profile
            profile.phone = request.POST.get('phone', '')
            profile.address = request.POST.get('address', '')
            profile.city = request.POST.get('city', '')
            profile.country = request.POST.get('country', 'Rwanda')
            profile.newsletter_subscribed = request.POST.get('newsletter') == 'on'
            
            # Handle avatar
            if request.POST.get('remove_avatar') == '1' and profile.profile_picture:
                profile.profile_picture.delete()
                profile.profile_picture = None
            elif request.FILES.get('avatar'):
                if profile.profile_picture:
                    profile.profile_picture.delete()
                profile.profile_picture = request.FILES['avatar']
            
            profile.save()
            
            messages.success(request, f'User "{user.username}" updated successfully!')
            return redirect('products:admin_users')
            
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
            return redirect('products:admin_edit_user', user_id=user_id)
    
    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'products/admin/edit_user.html', context)

@staff_member_required
def admin_delete_user(request, user_id):
    """Delete user"""
    user = get_object_or_404(User, id=user_id)
    username = user.username
    
    # Don't allow deleting yourself
    if request.user.id == user_id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('products:admin_users')
    
    user.delete()
    messages.success(request, f'User "{username}" has been deleted.')
    return redirect('products:admin_users')

@staff_member_required
def admin_check_username(request):
    """Check if username exists (AJAX)"""
    username = request.GET.get('username')
    user_id = request.GET.get('user_id')
    
    if user_id:
        exists = User.objects.exclude(id=user_id).filter(username=username).exists()
    else:
        exists = User.objects.filter(username=username).exists()
    
    return JsonResponse({'exists': exists})



@login_required
def seller_register(request):
    """Register as a seller"""
    # Check if user is already a seller
    if hasattr(request.user, 'seller_profile'):
        messages.info(request, 'You are already registered as a seller.')
        return redirect('products:seller_dashboard')
    
    if request.method == 'POST':
        try:
            store_name = request.POST.get('store_name')
            store_slug = slugify(store_name)
            store_description = request.POST.get('store_description')
            phone = request.POST.get('phone')
            address = request.POST.get('address')
            city = request.POST.get('city')
            payment_method = request.POST.get('payment_method')
            payment_account = request.POST.get('payment_account')
            
            # Ensure unique slug
            original_slug = store_slug
            counter = 1
            while Seller.objects.filter(store_slug=store_slug).exists():
                store_slug = f"{original_slug}-{counter}"
                counter += 1
            
            seller = Seller.objects.create(
                user=request.user,
                store_name=store_name,
                store_slug=store_slug,
                store_description=store_description,
                phone=phone,
                email=request.user.email,
                address=address,
                city=city,
                payment_method=payment_method,
                payment_account=payment_account
            )
            
            # Handle logo upload
            if request.FILES.get('store_logo'):
                seller.store_logo = request.FILES['store_logo']
                seller.save()
            
            messages.success(request, f'Congratulations! Your seller account "{store_name}" has been created. Please wait for verification.')
            return redirect('products:seller_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error creating seller account: {str(e)}')
    
    return render(request, 'products/seller/register.html')

@login_required
def seller_dashboard(request):
    """Seller dashboard to manage products"""
    from products.models import Product
    
    # Make sure the user is a seller
    if not request.user.is_seller:
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('home')
    
    if not request.user.is_approved:
        messages.warning(request, 'Your account is pending approval.')
        return redirect('home')
    
    # Get products belonging to this seller
    products = Product.objects.filter(seller=request.user).order_by('-created')
    
    context = {
        'products': products,
        'total_products': products.count(),
        'active_products': products.filter(is_approved=True).count(),
        'pending_products': products.filter(is_approved=False).count(),
    }
    # Use the correct template path - points to products/seller/seller_dashboard.html
    return render(request, 'products/seller/seller_dashboard.html', context)
@login_required
def register_seller(request):
    if request.method == 'POST':
        # Get form data directly
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        store_name = request.POST.get('store_name')
        store_description = request.POST.get('store_description')
        phone = request.POST.get('phone')
        address = request.POST.get('address')
        city = request.POST.get('city')
        payment_method = request.POST.get('payment_method')
        payment_account = request.POST.get('payment_account')
        
        # Validate passwords
        if password1 != password2:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'accounts/register_seller.html')
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists!')
            return render(request, 'accounts/register_seller.html')
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists!')
            return render(request, 'accounts/register_seller.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', ''),
            role='seller',
            is_approved=True,  # Auto-approve
            seller_approved_at=timezone.now(),
            business_name=store_name,
            business_description=store_description,
            phone_number=phone,
            address=f"{address}, {city}" if city else address
        )
        
        # Handle store logo
        if 'store_logo' in request.FILES:
            user.business_logo = request.FILES['store_logo']
            user.save()
        
        # Create seller profile
        profile = SellerProfile.objects.create(
            user=user,
            payment_method=payment_method,
            payment_account=payment_account,
            city=city,
            commission_rate=10.00
        )
        
        messages.success(request, 'Congratulations! Your seller account is ready! You can now add products.')
        return redirect('login')
    
    return render(request, 'accounts/register_seller.html')

@login_required
def seller_edit_product(request, product_id):
    """Edit seller product"""
    product = get_object_or_404(SellerProduct, id=product_id, seller__user=request.user)
    
    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.category_id = request.POST.get('category')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.sale_price = request.POST.get('sale_price') or None
        product.stock = request.POST.get('stock')
        product.on_sale = request.POST.get('on_sale') == 'on'
        product.featured = request.POST.get('featured') == 'on'
        product.available = request.POST.get('available') == 'on'
        
        # Handle images
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        if request.FILES.get('image_2'):
            product.image_2 = request.FILES['image_2']
        if request.FILES.get('image_3'):
            product.image_3 = request.FILES['image_3']
        
        product.save()
        messages.success(request, f'Product "{product.name}" updated successfully!')
        return redirect('products:seller_products')
    
    categories = Category.objects.all()
    return render(request, 'products/seller/edit_product.html', {'product': product, 'categories': categories})

@login_required
def seller_delete_product(request, product_id):
    """Delete seller product"""
    product = get_object_or_404(SellerProduct, id=product_id, seller__user=request.user)
    product_name = product.name
    product.delete()
    messages.success(request, f'Product "{product_name}" deleted successfully!')
    return redirect('products:seller_products')
@login_required
def seller_orders(request):
    """View for sellers to see orders for their products"""
    if not request.user.is_seller or not request.user.is_approved:
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('home')
    
    from orders.models import Order, OrderItem
    
    # Get all order items for seller's products
    order_items = OrderItem.objects.filter(product__seller=request.user).select_related('order', 'order__user')
    
    # Get unique orders from these order items
    order_ids = order_items.values_list('order_id', flat=True).distinct()
    orders = Order.objects.filter(id__in=order_ids).order_by('-created')
    
    # Calculate statistics
    total_orders = orders.count()
    pending_orders = orders.filter(status='pending').count()
    processing_orders = orders.filter(status='processing').count()
    completed_orders = orders.filter(status='delivered').count()
    
    # Attach items to each order for the template
    for order in orders:
        order.seller_items = order_items.filter(order=order)
    
    context = {
        'orders': orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'processing_orders': processing_orders,
        'completed_orders': completed_orders,
    }
    return render(request, 'products/seller/orders.html', context)

@login_required
def seller_settings(request):
    """Seller account settings"""
    if not hasattr(request.user, 'seller_profile'):
        return redirect('products:seller_register')
    
    seller = request.user.seller_profile
    
    if request.method == 'POST':
        seller.store_name = request.POST.get('store_name')
        seller.store_description = request.POST.get('store_description')
        seller.phone = request.POST.get('phone')
        seller.address = request.POST.get('address')
        seller.city = request.POST.get('city')
        seller.country = request.POST.get('country')
        seller.payment_method = request.POST.get('payment_method')
        seller.payment_account = request.POST.get('payment_account')
        
        if request.FILES.get('store_logo'):
            seller.store_logo = request.FILES['store_logo']
        if request.FILES.get('store_banner'):
            seller.store_banner = request.FILES['store_banner']
        
        seller.save()
        messages.success(request, 'Store settings updated successfully!')
        return redirect('products:seller_settings')
    
    return render(request, 'products/seller/settings.html', {'seller': seller})

def seller_store(request, store_slug):
    """Public seller store page"""
    seller = get_object_or_404(Seller, store_slug=store_slug, is_active=True, is_verified=True)
    products = seller.products.filter(available=True).order_by('-created')
    
    context = {
        'seller': seller,
        'products': products,
    }
    return render(request, 'products/seller/store.html', context)

def seller_product_detail(request, slug):
    """Public seller product detail page"""
    product = get_object_or_404(SellerProduct, slug=slug, available=True)
    
    context = {
        'product': product,
        'seller': product.seller,
    }
    return render(request, 'products/seller/product_detail.html', context)

# Seller Views for Products app
@login_required
def seller_products(request):
    """View for sellers to see their products"""
    if not request.user.is_seller or not request.user.is_approved:
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('home')
    
    products = Product.objects.filter(seller=request.user).order_by('-created')
    
    context = {
        'products': products,
        'total_products': products.count(),
    }
    # Use correct path with seller subfolder
    return render(request, 'products/seller/seller_products.html', context)

@login_required
def seller_add_product(request):
    """View for sellers to add new products"""
    if not request.user.is_seller or not request.user.is_approved:
        messages.error(request, 'You need to be an approved seller to add products.')
        return redirect('home')
    
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        category_id = request.POST.get('category')
        stock = request.POST.get('stock', 0)  # Changed from stock_quantity to stock
        image = request.FILES.get('image')
        image_2 = request.FILES.get('image_2')
        image_3 = request.FILES.get('image_3')
        
        # Validate data
        if not all([name, description, price, category_id]):
            messages.error(request, 'Please fill in all required fields.')
            return redirect('products:seller_add_product')
        
        try:
            category = Category.objects.get(id=category_id)
            
            # Create product
            product = Product.objects.create(
                name=name,
                description=description,
                price=price,
                category=category,
                seller=request.user,
                stock=stock,  # Changed from stock_quantity to stock
                is_approved=False,  # Requires admin approval
                available=True
            )
            
            # Handle images
            if image:
                product.image = image
            if image_2:
                product.image_2 = image_2
            if image_3:
                product.image_3 = image_3
            product.save()
            
            messages.success(request, 'Product added successfully! Admin will review it shortly.')
            return redirect('products:seller_dashboard')  # Changed from seller_products to seller_dashboard
            
        except Category.DoesNotExist:
            messages.error(request, 'Selected category does not exist.')
        except Exception as e:
            messages.error(request, f'Error adding product: {str(e)}')
    
    categories = Category.objects.all()
    return render(request, 'products/seller/add_product.html', {'categories': categories})


@login_required
def seller_edit_product(request, product_id):
    """View for sellers to edit their products"""
    if not request.user.is_seller or not request.user.is_approved:
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('home')
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        # Update product fields
        product.name = request.POST.get('name')
        product.description = request.POST.get('description')
        product.price = request.POST.get('price')
        product.stock = request.POST.get('stock')
        product.available = request.POST.get('available') == 'on'
        product.on_sale = request.POST.get('on_sale') == 'on'
        
        sale_price = request.POST.get('sale_price')
        if sale_price:
            product.sale_price = sale_price
        
        category_id = request.POST.get('category')
        if category_id:
            product.category = get_object_or_404(Category, id=category_id)
        
        # Handle images
        if request.FILES.get('image'):
            product.image = request.FILES['image']
        if request.FILES.get('image_2'):
            product.image_2 = request.FILES['image_2']
        if request.FILES.get('image_3'):
            product.image_3 = request.FILES['image_3']
        
        product.save()
        messages.success(request, 'Product updated successfully!')
        return redirect('products:seller_dashboard')
    
    categories = Category.objects.all()
    # Fix: Use the correct template path with seller subfolder
    return render(request, 'products/seller/edit_product.html', {
        'product': product,
        'categories': categories
    })
@login_required
def seller_delete_product(request, product_id):
    """View for sellers to delete their products"""
    if not request.user.is_seller or not request.user.is_approved:
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('home')
    
    product = get_object_or_404(Product, id=product_id, seller=request.user)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('products:seller_products')
    
    # Use the correct path with seller subfolder
    return render(request, 'products/seller/seller_delete_product.html', {'product': product})

@staff_member_required
def admin_seller_list(request):
    """Admin view to see all sellers"""
    sellers = User.objects.filter(role='seller').annotate(
        total_products=Count('products'),
    )
    
    context = {
        'sellers': sellers,
        'total_sellers': sellers.count(),
        'active_sellers': sellers.filter(is_approved=True).count(),
        'pending_sellers': sellers.filter(is_approved=False).count(),
    }
    # Make sure this template exists
    return render(request, 'products/admin/sellers.html', context)

@staff_member_required
def admin_seller_detail(request, seller_id):
    """Admin view to see seller details"""
    seller = get_object_or_404(User, id=seller_id, role='seller')
    products = seller.products.all()
    profile = seller.seller_profile if hasattr(seller, 'seller_profile') else None
    
    context = {
        'seller': seller,
        'products': products,
        'profile': profile,
        'total_products': products.count(),
    }
    return render(request, 'products/admin/seller_detail.html', context)

@staff_member_required
def admin_seller_requests(request):
    """Admin view for pending seller approvals"""
    pending_sellers = User.objects.filter(role='seller', is_approved=False)
    approved_sellers = User.objects.filter(role='seller', is_approved=True)
    
    context = {
        'pending_sellers': pending_sellers,
        'approved_sellers': approved_sellers,
    }
    return render(request, 'products/admin/seller_requests.html', context)

@staff_member_required
def admin_approve_seller(request, seller_id):
    """Approve a seller"""
    seller = get_object_or_404(User, id=seller_id, role='seller')
    seller.is_approved = True
    seller.seller_approved_at = timezone.now()
    seller.save()
    
    messages.success(request, f'{seller.business_name} has been approved as a seller!')
    return redirect('products:admin_seller_requests')

@staff_member_required
def admin_reject_seller(request, seller_id):
    """Reject a seller application"""
    seller = get_object_or_404(User, id=seller_id, role='seller', is_approved=False)
    username = seller.username
    seller.delete()
    
    messages.success(request, f'{username}\'s seller application has been rejected.')
    return redirect('products:admin_seller_requests')


def search_products_api(request):
    """API endpoint for live product and category search"""
    query = request.GET.get('q', '').strip()
    
    if not query or len(query) < 2:
        return JsonResponse({'products': [], 'categories': [], 'suggestions': []})
    
    # Search products (don't filter by is_approved for testing)
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query)
    )[:10]  # Limit to 10 products
    
    # Search categories
    categories = Category.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query)
    ).annotate(product_count=Count('products'))[:5]
    
    # Get search suggestions from product names
    suggestions = list(Product.objects.filter(
        name__icontains=query
    ).values_list('name', flat=True)[:5])
    
    # Prepare products data
    products_data = []
    for product in products:
        products_data.append({
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'price': float(product.price),
            'sale_price': float(product.sale_price) if product.sale_price else None,
            'image': product.image.url if product.image else None,
            'category_name': product.category.name if product.category else None,
        })
    
    # Prepare categories data
    categories_data = []
    for category in categories:
        categories_data.append({
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'product_count': category.product_count,
        })
    
    return JsonResponse({
        'products': products_data,
        'categories': categories_data,
        'suggestions': suggestions,
        'total_products': products.count(),
        'total_categories': categories.count(),
    })