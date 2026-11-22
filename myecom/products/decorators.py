# products/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.shortcuts import redirect

def admin_required(view_func):
    """Decorator to ensure only admin users can access the view"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access the admin panel.')
            return redirect('accounts:login')
        
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'You do not have permission to access the admin panel.')
            return redirect('products:home')
        
        return view_func(request, *args, **kwargs)
    return wrapper

# Alternative using Django's built-in decorator
from django.contrib.admin.views.decorators import staff_member_required
# @staff_member_required  # This also works for staff users