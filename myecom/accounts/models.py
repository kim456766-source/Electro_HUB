from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('seller', 'Seller'),
        ('admin', 'Admin'),
    )
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='custom_user_set',
        related_query_name='custom_user',
    )
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    is_approved = models.BooleanField(default=False)
    seller_approved_at = models.DateTimeField(null=True, blank=True)
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_description = models.TextField(blank=True, null=True)
    business_logo = models.ImageField(upload_to='business_logos/', blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    @property
    def is_seller(self):
        return self.role == 'seller'
    
    @property
    def is_approved_seller(self):
        return self.is_seller and self.is_approved


class SellerProfile(models.Model):
    PAYMENT_METHODS = (
        ('mtn_money', 'MTN Money'),
        ('bank_transfer', 'Bank Transfer'),
        ('paypal', 'PayPal'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    
    # Statistics
    total_products = models.IntegerField(default=0)
    total_sales = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    commission_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Payout information
    last_payout_date = models.DateTimeField(null=True, blank=True)
    total_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment details
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, null=True, blank=True)
    payment_account = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    
    # Timestamps
    joined_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Seller Profile: {self.user.username}"
    
    def update_balance(self):
        """Update seller's balance due"""
        self.balance_due = self.commission_earned - self.total_paid
        self.save()
    
    def update_stats(self):
        """Update seller statistics from orders"""
        from orders.models import OrderItem
        
        order_items = OrderItem.objects.filter(product__seller=self.user)
        self.total_sales = order_items.count()
        total = order_items.aggregate(total=models.Sum('price'))['total']
        self.total_revenue = total if total else 0
        commission = order_items.aggregate(total=models.Sum('seller_commission'))['total']
        self.commission_earned = commission if commission else 0
        self.total_products = self.user.products.filter(is_approved=True).count()
        self.update_balance()
        self.save()
    
    class Meta:
        ordering = ['-joined_date']


class Profile(models.Model):
    """User profile for additional information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True, default='Rwanda')
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    newsletter_subscribed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Profile of {self.user.username}"


class LoginHistory(models.Model):
    """Track user login history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_history')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    login_time = models.DateTimeField(auto_now_add=True)
    login_successful = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Login History'
        verbose_name_plural = 'Login Histories'
        ordering = ['-login_time']
    
    def __str__(self):
        return f"{self.user.username} logged in at {self.login_time}"


class Wishlist(models.Model):
    """User wishlist for products"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist')
    product = models.ForeignKey('products.Product', on_delete=models.CASCADE, related_name='wishlisted_by')
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Wishlist'
        verbose_name_plural = 'Wishlists'
        unique_together = ['user', 'product']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class PasswordResetCode(models.Model):
    """Store OTP codes for password reset"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_codes')
    code = models.CharField(max_length=6, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Password Reset Code'
        verbose_name_plural = 'Password Reset Codes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reset code for {self.user.username} - {self.code}"
    
    def is_valid(self):
        """Check if the code is still valid"""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()


# ========== SIGNALS ==========

@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    """Create Profile and SellerProfile when user is created"""
    if created:
        # Create Profile for every user
        Profile.objects.get_or_create(user=instance)
        
        # Create SellerProfile only for sellers
        if instance.role == 'seller':
            SellerProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profiles(sender, instance, **kwargs):
    """Save profiles when user is saved"""
    # Save Profile
    if hasattr(instance, 'profile'):
        instance.profile.save()
    
    # Save SellerProfile for sellers
    if instance.role == 'seller':
        if not hasattr(instance, 'seller_profile'):
            SellerProfile.objects.create(user=instance)
        else:
            instance.seller_profile.save()