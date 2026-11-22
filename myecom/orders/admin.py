from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import Order, OrderItem, Payment

class OrderItemInline(admin.TabularInline):
    """Inline admin for order items"""
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0
    readonly_fields = ['price', 'quantity', 'get_cost']
    
    def get_cost(self, obj):
        """Display item total cost"""
        return f'${obj.get_cost()}'
    get_cost.short_description = 'Total'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin configuration for Order model"""
    
    # Fields to display in list view - UPDATED: removed 'paid'
    list_display = [
        'id', 
        'order_number',
        'user', 
        'full_name', 
        'email', 
        'phone', 
        'city', 
        'payment_method',  # Added
        'payment_status',  # Added instead of 'paid'
        'status', 
        'get_total', 
        'created'
    ]
    
    # Fields that can be clicked to edit
    list_display_links = ['id', 'order_number', 'user']
    
    # Fields that can be edited directly in list view - UPDATED: removed 'paid'
    list_editable = ['status', 'payment_status']
    
    # Filters sidebar - UPDATED: replaced 'paid' with 'payment_status'
    list_filter = ['status', 'payment_status', 'payment_method', 'created', 'city']
    
    # Search fields
    search_fields = [
        'id', 
        'order_number',
        'user__username', 
        'user__email', 
        'first_name', 
        'last_name', 
        'email', 
        'phone'
    ]
    
    # Date hierarchy
    date_hierarchy = 'created'
    
    # Readonly fields
    readonly_fields = ['order_number', 'created', 'updated', 'subtotal', 'shipping_cost', 'tax', 'total']
    
    # Fieldsets for organizing the form - UPDATED: reorganized with new fields
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'notes')
        }),
        ('Customer Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Shipping Address', {
            'fields': ('address', 'city', 'postal_code', 'country')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_status', 'payment_id'),
            'classes': ('wide',)
        }),
        ('Financial Summary', {
            'fields': ('subtotal', 'shipping_cost', 'tax', 'total'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    
    # Inline items
    inlines = [OrderItemInline]
    
    # Pagination
    list_per_page = 25
    
    # Actions
    actions = [
        'mark_as_processing', 
        'mark_as_shipped', 
        'mark_as_delivered', 
        'mark_as_cancelled',
        'mark_payment_completed',
        'mark_payment_failed',
        'send_status_email'
    ]
    
    def full_name(self, obj):
        """Display customer full name"""
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Customer Name'
    
    def get_total(self, obj):
        """Display order total"""
        return f'${obj.total}'
    get_total.short_description = 'Total'
    
    def payment_status_colored(self, obj):
        """Display colored payment status"""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'refunded': 'purple'
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_colored.short_description = 'Payment Status'
    payment_status_colored.admin_order_field = 'payment_status'
    
    def status_colored(self, obj):
        """Display colored order status"""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'shipped': 'purple',
            'delivered': 'green',
            'cancelled': 'red'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    # Action methods
    def mark_as_processing(self, request, queryset):
        """Mark orders as processing"""
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} orders marked as processing.')
    mark_as_processing.short_description = "Mark selected as processing"
    
    def mark_as_shipped(self, request, queryset):
        """Mark orders as shipped"""
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} orders marked as shipped.')
    mark_as_shipped.short_description = "Mark selected as shipped"
    
    def mark_as_delivered(self, request, queryset):
        """Mark orders as delivered"""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} orders marked as delivered.')
    mark_as_delivered.short_description = "Mark selected as delivered"
    
    def mark_as_cancelled(self, request, queryset):
        """Mark orders as cancelled"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} orders marked as cancelled.')
    mark_as_cancelled.short_description = "Mark selected as cancelled"
    
    def mark_payment_completed(self, request, queryset):
        """Mark payment as completed"""
        updated = queryset.update(payment_status='completed')
        self.message_user(request, f'{updated} orders marked as payment completed.')
    mark_payment_completed.short_description = "Mark payment as completed"
    
    def mark_payment_failed(self, request, queryset):
        """Mark payment as failed"""
        updated = queryset.update(payment_status='failed')
        self.message_user(request, f'{updated} orders marked as payment failed.')
    mark_payment_failed.short_description = "Mark payment as failed"
    
    def send_status_email(self, request, queryset):
        """Send status update email to customers"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        sent = 0
        for order in queryset:
            if order.email:
                subject = f'Order #{order.order_number} Status Update'
                message = f"""
                Dear {order.first_name},
                
                Your order status has been updated to: {order.get_status_display()}
                
                Order Details:
                Order Number: {order.order_number}
                Status: {order.get_status_display()}
                Payment Status: {order.get_payment_status_display()}
                
                You can track your order at: http://127.0.0.1:8000/orders/track/{order.id}/
                
                Thank you for shopping with us!
                
                Best regards,
                MyEcom Team
                """
                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [order.email],
                        fail_silently=False,
                    )
                    sent += 1
                except Exception as e:
                    self.message_user(request, f'Failed to send email for order #{order.order_number}: {str(e)}', level='ERROR')
        
        self.message_user(request, f'Status emails sent for {sent} orders.')
    send_status_email.short_description = "Send status email to customers"
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly for existing orders"""
        if obj:  # Editing existing order
            return self.readonly_fields + ['order_number', 'user', 'subtotal', 'shipping_cost', 'tax', 'total']
        return self.readonly_fields
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of orders"""
        return False

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin configuration for OrderItem model"""
    
    list_display = ['id', 'order_link', 'product', 'quantity', 'price', 'get_cost']
    list_filter = ['order__status', 'order__payment_status', 'order__payment_method']
    search_fields = ['order__order_number', 'product__name', 'order__user__username']
    raw_id_fields = ['product', 'order']
    readonly_fields = ['price', 'quantity']
    list_per_page = 30
    
    def order_link(self, obj):
        """Link to the order"""
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    
    def get_cost(self, obj):
        """Display item total cost"""
        return f'${obj.get_cost()}'
    get_cost.short_description = 'Total'
    
    def has_add_permission(self, request):
        """Prevent adding order items directly"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting order items directly"""
        return False
    
    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('order', 'product')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model"""
    
    list_display = [
        'id', 
        'order_link', 
        'payment_method', 
        'amount', 
        'status_colored', 
        'transaction_id',
        'created'
    ]
    list_filter = ['payment_method', 'status', 'created']
    search_fields = ['order__order_number', 'transaction_id', 'phone_number']
    readonly_fields = ['created', 'updated']
    list_per_page = 20
    
    def order_link(self, obj):
        """Link to the order"""
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html('<a href="{}">Order #{}</a>', url, obj.order.order_number)
    order_link.short_description = 'Order'
    
    def status_colored(self, obj):
        """Display colored status"""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'refunded': 'purple'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    status_colored.admin_order_field = 'status'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('order', 'payment_method', 'amount', 'status', 'transaction_id')
        }),
        ('MTN Money Details', {
            'fields': ('phone_number',),
            'classes': ('collapse',),
            'description': 'MTN Money payment details'
        }),
        ('Card Details', {
            'fields': ('card_last4', 'card_brand'),
            'classes': ('collapse',),
            'description': 'Credit/Debit card details'
        }),
        ('Crypto Details', {
            'fields': ('crypto_address', 'crypto_network'),
            'classes': ('collapse',),
            'description': 'Cryptocurrency payment details'
        }),
        ('Timestamps', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Prevent adding payments directly"""
        return False
    
    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for existing payments"""
        if obj:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields