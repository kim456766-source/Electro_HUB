from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    show_in_menu = models.BooleanField(default=True, help_text="Display this category in the navigation menu")
    
    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('products:product_list_by_category', args=[self.slug])
    
    def product_count(self):
        """Return number of available products in this category"""
        return self.products.filter(available=True).count()
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided and ensure uniqueness."""
        if not self.slug:
            self.slug = slugify(self.name)
        else:
            self.slug = slugify(self.slug)

        original_slug = self.slug
        counter = 1
        while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(
        Category, 
        related_name='products', 
        on_delete=models.CASCADE,
        help_text="Select category for this product"
    )
    
    # ADD THIS FIELD - Link product to seller
    seller = models.ForeignKey(
        'accounts.User',  # or settings.AUTH_USER_MODEL
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True,
        help_text="Seller who listed this product"
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        blank=True, 
        null=True,
        help_text="Discounted price (if on sale)"
    )
    
    # Images
    image = models.ImageField(upload_to='products/', help_text="Main product image")
    image_2 = models.ImageField(upload_to='products/', blank=True, null=True, help_text="Additional image 1")
    image_3 = models.ImageField(upload_to='products/', blank=True, null=True, help_text="Additional image 2")
    
    # Inventory
    stock = models.PositiveIntegerField(default=0, help_text="Current stock quantity")
    available = models.BooleanField(default=True, help_text="Is product available for purchase?")
    
    # Featured and Sale flags
    featured = models.BooleanField(default=False, help_text="Show on homepage featured section")
    on_sale = models.BooleanField(default=False, help_text="Is product currently on sale?")
    
    # Admin approval for seller products
    is_approved = models.BooleanField(default=False, help_text="Has admin approved this product?")
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created']
        indexes = [
            models.Index(fields=['id', 'slug']),
            models.Index(fields=['-created']),
            models.Index(fields=['available']),
            models.Index(fields=['seller']),  # Add index for seller queries
        ]
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('products:product_detail', args=[self.slug])
    
    def get_price(self):
        """Return sale price if on sale and sale_price exists, otherwise return regular price"""
        if self.on_sale and self.sale_price:
            return self.sale_price
        return self.price
    
    def get_discount_percentage(self):
        """Calculate discount percentage if on sale"""
        if self.on_sale and self.sale_price and self.price > 0:
            discount = ((self.price - self.sale_price) / self.price) * 100
            return round(discount)
        return 0
    
    def is_in_stock(self):
        """Check if product is in stock"""
        return self.stock > 0
    
    def has_multiple_images(self):
        """Check if product has additional images"""
        return bool(self.image_2 or self.image_3)
    
    def get_all_images(self):
        """Return list of all product images"""
        images = []
        if self.image:
            images.append(self.image)
        if self.image_2:
            images.append(self.image_2)
        if self.image_3:
            images.append(self.image_3)
        return images
    
    def reduce_stock(self, quantity):
        """Reduce stock when order is placed"""
        if self.stock >= quantity:
            self.stock -= quantity
            self.save()
            return True
        return False
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided and ensure uniqueness."""
        if not self.slug:
            self.slug = slugify(self.name)
        else:
            self.slug = slugify(self.slug)

        original_slug = self.slug
        counter = 1
        while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        super().save(*args, **kwargs)


class ProductReview(models.Model):
    """Model for product reviews and ratings"""
    product = models.ForeignKey(Product, related_name='reviews', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='product_reviews', on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created']
        unique_together = ['product', 'user']  # One review per user per product
    
    def __str__(self):
        return f"{self.user.username}'s review of {self.product.name}"
    
    def get_rating_stars(self):
        """Return HTML stars for rating"""
        stars = ''
        for i in range(1, 6):
            if i <= self.rating:
                stars += '★'
            else:
                stars += '☆'
        return stars


class ProductSpecification(models.Model):
    """Model for product specifications (like color, size, weight, etc.)"""
    product = models.ForeignKey(Product, related_name='specifications', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="Specification name (e.g., Color, Size, Weight)")
    value = models.CharField(max_length=200, help_text="Specification value (e.g., Red, Large, 1kg)")
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name}: {self.value}"


class ProductImage(models.Model):
    """Additional images for products - NO user field to avoid conflict"""
    product = models.ForeignKey(Product, related_name='additional_images', on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to='products/additional/', blank=True, null=True)
    alt_text = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Image for {self.product.name if self.product else 'Unknown'}"


# ==================== SELLER MODELS ====================

class Seller(models.Model):
    """Seller/Vendor model for marketplace"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='seller_store')
    store_name = models.CharField(max_length=200)
    store_slug = models.SlugField(unique=True)
    store_logo = models.ImageField(upload_to='sellers/logos/', blank=True, null=True)
    store_banner = models.ImageField(upload_to='sellers/banners/', blank=True, null=True)
    store_description = models.TextField(blank=True)
    
    # Contact Information
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, default='Rwanda')
    
    # Payment Details
    payment_method = models.CharField(max_length=50, choices=[
        ('mtn_money', 'MTN Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
    ], default='mtn_money')
    payment_account = models.CharField(max_length=100, help_text="MTN number, Bank account, or PayPal email")
    
    # Store Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Statistics
    total_sales = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_orders = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.store_name
    
    def get_absolute_url(self):
        return reverse('products:seller_store', args=[self.store_slug])
    
    def update_stats(self):
        """Update seller statistics"""
        from orders.models import OrderItem
        seller_products = self.products.filter(available=True)
        order_items = OrderItem.objects.filter(product__in=seller_products, order__status='delivered')
        self.total_orders = order_items.count()
        self.total_sales = sum(item.get_cost() for item in order_items)
        self.save()


class SellerProduct(models.Model):
    """Product model for sellers"""
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # Images
    image = models.ImageField(upload_to='seller_products/')
    image_2 = models.ImageField(upload_to='seller_products/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='seller_products/', blank=True, null=True)
    
    # Inventory
    stock = models.PositiveIntegerField(default=0)
    available = models.BooleanField(default=True)
    on_sale = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    
    # Commission
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    seller_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f"{self.seller.store_name} - {self.name}"
    
    def get_absolute_url(self):
        return reverse('products:seller_product_detail', args=[self.slug])
    
    def get_price(self):
        if self.on_sale and self.sale_price:
            return self.sale_price
        return self.price
    
    def calculate_commission(self):
        """Calculate platform commission"""
        return (self.get_price() * self.commission_rate) / 100
    
    def calculate_seller_earning(self):
        """Calculate seller's earnings after commission"""
        return self.get_price() - self.calculate_commission()


class SellerOrder(models.Model):
    """Order tracking for sellers"""
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='orders')
    order = models.ForeignKey('orders.Order', on_delete=models.CASCADE, related_name='seller_orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission = models.DecimalField(max_digits=10, decimal_places=2)
    seller_earning = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Order for {self.seller.store_name} - ${self.seller_earning}"