from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin configuration for Category model"""
    list_display = ['name', 'slug', 'product_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_per_page = 20
    
    def product_count(self, obj):
        """Display number of products in category"""
        return obj.products.count()
    product_count.short_description = 'Products'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin configuration for Product model"""
    
    # Fields to display in list view
    list_display = [
        'id', 'name', 'category', 'price', 'sale_price', 
        'stock', 'available', 'featured', 'on_sale', 'created'
    ]
    
    # Fields that can be clicked to edit
    list_display_links = ['id', 'name']
    
    # Fields that can be edited directly in list view
    list_editable = ['price', 'sale_price', 'stock', 'available', 'featured', 'on_sale']
    
    # Filters sidebar
    list_filter = ['available', 'featured', 'on_sale', 'category', 'created']
    
    # Search fields
    search_fields = ['name', 'description', 'slug']
    
    # Automatic slug generation from name
    prepopulated_fields = {'slug': ('name',)}
    
    # Pagination
    list_per_page = 25
    
    # Date hierarchy for browsing
    date_hierarchy = 'created'
    
    # Fieldsets for organizing the form
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'sale_price', 'on_sale'),
            'classes': ('wide',)
        }),
        ('Inventory', {
            'fields': ('stock', 'available'),
            'classes': ('wide',)
        }),
        ('Images', {
            'fields': ('image', 'image_2', 'image_3'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('featured',),
            'classes': ('wide',)
        }),
    )
    
    # Actions dropdown
    actions = ['make_available', 'make_unavailable', 'make_featured', 'remove_featured']
    
    def make_available(self, request, queryset):
        """Make selected products available"""
        updated = queryset.update(available=True)
        self.message_user(request, f'{updated} products marked as available.')
    make_available.short_description = "Mark selected as available"
    
    def make_unavailable(self, request, queryset):
        """Make selected products unavailable"""
        updated = queryset.update(available=False)
        self.message_user(request, f'{updated} products marked as unavailable.')
    make_unavailable.short_description = "Mark selected as unavailable"
    
    def make_featured(self, request, queryset):
        """Make selected products featured"""
        updated = queryset.update(featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    make_featured.short_description = "Mark selected as featured"
    
    def remove_featured(self, request, queryset):
        """Remove featured status from selected products"""
        updated = queryset.update(featured=False)
        self.message_user(request, f'{updated} products removed from featured.')
    remove_featured.short_description = "Remove featured from selected"
