from django.conf import settings
from django.db import models
from products.models import Product
from django.utils import timezone
import uuid

class Order(models.Model):
    """Model for customer orders"""
    
    # Payment Method Choices
    PAYMENT_METHOD_CHOICES = [
        ('mtn_money', 'MTN Money'),
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('bitcoin', 'Bitcoin'),
        ('ethereum', 'Ethereum'),
        ('paypal', 'PayPal'),
    ]
    
    # Payment Status Choices
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Order Status Choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Order fields
    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    
    # Customer Information
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Shipping Address
    address = models.CharField(max_length=250)
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='Rwanda')
    
    # Payment Information
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='mtn_money')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_id = models.CharField(max_length=100, blank=True, null=True)  # Transaction ID from payment gateway
    
    # Order Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Financial
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    # Notes
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created']
    
    def __str__(self):
        return f'Order #{self.order_number} - {self.user.username}'
    
    def save(self, *args, **kwargs):
        """Generate order number if not exists"""
        if not self.order_number:
            # Generate unique order number: ORD-YYYYMMDD-XXXX
            today = timezone.now().strftime('%Y%m%d')
            random_part = str(uuid.uuid4()).upper()[:6]
            self.order_number = f'ORD-{today}-{random_part}'
        super().save(*args, **kwargs)
    
    def get_total_cost(self):
        """Calculate total cost of all items"""
        return sum(item.get_cost() for item in self.items.all())
    
    def update_totals(self):
        """Update order totals"""
        self.subtotal = self.get_total_cost()
        self.total = self.subtotal + self.shipping_cost + self.tax
        self.save()

class OrderItem(models.Model):
    """Model for items in an order"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f'{self.quantity} x {self.product.name}'
    
    def get_cost(self):
        return self.price * self.quantity

class Payment(models.Model):
    """Model for tracking payments"""
    PAYMENT_GATEWAY_CHOICES = [
        ('mtn_money', 'MTN Money'),
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('bitcoin', 'Bitcoin'),
        ('ethereum', 'Ethereum'),
        ('paypal', 'PayPal'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_GATEWAY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Payment details (encrypted in production)
    phone_number = models.CharField(max_length=20, blank=True, null=True)  # For MTN Money
    card_last4 = models.CharField(max_length=4, blank=True, null=True)  # For Visa/Mastercard
    card_brand = models.CharField(max_length=20, blank=True, null=True)  # Visa, Mastercard
    crypto_address = models.CharField(max_length=100, blank=True, null=True)  # For crypto
    crypto_network = models.CharField(max_length=20, blank=True, null=True)  # Bitcoin, Ethereum
    
    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f'Payment for Order #{self.order.order_number} - {self.payment_method}'