from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, SellerProfile, Profile, LoginHistory, Wishlist

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_approved', 'business_name', 'date_joined')
    list_filter = ('role', 'is_approved', 'is_active')
    search_fields = ('username', 'email', 'business_name')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Seller Info', {
            'fields': ('role', 'is_approved', 'seller_approved_at', 'business_name', 
                      'business_description', 'business_logo', 'phone_number', 'address'),
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Seller Info', {
            'fields': ('role', 'business_name', 'phone_number'),
        }),
    )

class SellerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_products', 'total_sales', 'total_revenue', 
                    'commission_rate', 'joined_date')
    list_filter = ('commission_rate', 'joined_date')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('joined_date', 'updated_at')

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'city', 'country', 'email_verified', 'created_at']
    list_filter = ['country', 'email_verified', 'newsletter_subscribed', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone', 'city']
    readonly_fields = ['created_at', 'updated_at', 'last_activity']

@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'ip_address', 'login_time', 'login_successful']
    list_filter = ['login_successful', 'login_time']
    search_fields = ['user__username', 'ip_address']
    readonly_fields = ['login_time']

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']
    readonly_fields = ['added_at']

# Register models
admin.site.register(User, CustomUserAdmin)
admin.site.register(SellerProfile, SellerProfileAdmin)