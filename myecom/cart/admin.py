from django.contrib import admin
# from .models import Cart, CartItem

# class CartItemInline(admin.TabularInline):
#     """Inline admin for cart items"""
#     model = CartItem
#     raw_id_fields = ['product']
#     extra = 0
#     readonly_fields = ['get_cost']
    
#     def get_cost(self, obj):
#         """Display item total cost"""
#         return obj.get_cost()
#     get_cost.short_description = 'Total'

# @admin.register(Cart)
# class CartAdmin(admin.ModelAdmin):
#     """Admin configuration for Cart model"""
    
#     list_display = ['id', 'user', 'item_count', 'total_price', 'created_at', 'updated_at']
#     list_filter = ['created_at', 'updated_at']
#     search_fields = ['user__username', 'user__email']
#     readonly_fields = ['created_at', 'updated_at']
#     inlines = [CartItemInline]
#     list_per_page = 20
    
#     def item_count(self, obj):
#         """Display number of items in cart"""
#         return obj.items.count()
#     item_count.short_description = 'Items'
    
#     def total_price(self, obj):
#         """Display cart total"""
#         return f'${obj.total_price()}'
#     total_price.short_description = 'Total'

# @admin.register(CartItem)
# class CartItemAdmin(admin.ModelAdmin):
#     """Admin configuration for CartItem model"""
    
#     list_display = ['id', 'cart', 'product', 'quantity', 'get_cost']
#     list_filter = ['cart__user']
#     search_fields = ['product__name', 'cart__user__username']
#     raw_id_fields = ['product', 'cart']
#     list_per_page = 20
    
#     def get_cost(self, obj):
#         """Display item total cost"""
#         return f'${obj.get_cost()}'
#     get_cost.short_description = 'Total'