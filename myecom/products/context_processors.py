from .models import Category
from django.db.models import Count, Q

def global_categories(request):
    """Make categories available to all templates"""
    categories = Category.objects.annotate(
        product_count=Count('products', filter=Q(products__available=True))
    ).all()[:5]  # Get top 5 categories for footer
    
    return {
        'global_categories': categories
    }