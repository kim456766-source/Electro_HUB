from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from django.views.decorators.debug import sensitive_post_parameters
from django.core.paginator import Paginator
from django.urls import reverse 
from django.utils.safestring import mark_safe 
from django.utils import timezone
from django.http import JsonResponse
import json
from .forms import (
    UserRegistrationForm, UserLoginForm, UserProfileForm,
    CustomPasswordChangeForm, PasswordResetRequestForm, SetPasswordForm, SellerRegistrationForm, UserRegistrationForm
)
from .models import Profile, LoginHistory, Wishlist, SellerProfile, PasswordResetCode
from .utils import send_verification_email, get_client_ip, create_password_reset_otp
from .tokens import account_activation_token
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from .forms import CustomerRegistrationForm, SellerRegistrationForm
from django.utils.http import urlsafe_base64_decode 

User = get_user_model()


# ==================== REGISTRATION & LOGIN ====
def register_customer(request):
    """Register a regular customer"""
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully! You can now login.')
            return redirect('accounts:login')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'accounts/register_customer.html', {'form': form})

def register_seller(request):
    """Register a new seller"""
    if request.method == 'POST':
        form = SellerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                
                # Update seller profile with payment info
                if hasattr(user, 'seller_profile'):
                    profile = user.seller_profile
                    profile.payment_method = form.cleaned_data.get('payment_method')
                    profile.payment_account = form.cleaned_data.get('payment_account')
                    profile.city = form.cleaned_data.get('city')
                    profile.save()
                
                # Success message
                messages.success(
                    request, 
                    '🎉 Congratulations! Your seller account has been created successfully! '
                    'You can now log in and start adding your products.'
                )
                return redirect('accounts:login')
                
            except Exception as e:
                messages.error(request, f'An error occurred: {str(e)}')
                return redirect('accounts:register_seller')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = SellerRegistrationForm()
    
    return render(request, 'accounts/register_seller.html', {'form': form})

def login_view(request):
    """User login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect sellers to their dashboard
            if user.role == 'seller' and user.is_approved:
                return redirect('products:seller_dashboard')
            else:
                return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'accounts/login.html')

@login_required
def profile_view(request):
    """User profile view"""
    return render(request, 'accounts/profile.html', {'user': request.user})

def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

# Alias for backward compatibility
def register(request):
    return register_customer(request)

def login_view(request):
    """
    User login view with login history tracking
    """
    if request.user.is_authenticated:
        return redirect('products:home')
    
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            remember_me = form.cleaned_data['remember_me']
            
            # Try to authenticate with username or email
            user = None
            if '@' in username:
                # Try email
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            else:
                # Try username
                user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    # Log in the user
                    login(request, user)
                    
                    # Set session expiry based on remember_me
                    if not remember_me:
                        request.session.set_expiry(0)  # Expire when browser closes
                    
                    # Record login history
                    LoginHistory.objects.create(
                        user=user,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        login_successful=True
                    )
                    
                    messages.success(request, f'Welcome back, {user.username}!')
                    
                    # Redirect to next page if provided
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('products:home')
                else:
                    messages.error(request, 'Your account is disabled.')
            else:
                messages.error(request, 'Invalid username or password.')
                
                # Record failed login attempt
                try:
                    user_obj = User.objects.get(email=username) if '@' in username else User.objects.get(username=username)
                    LoginHistory.objects.create(
                        user=user_obj,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        login_successful=False
                    )
                except User.DoesNotExist:
                    pass
        else:
            messages.error(request, 'Please fill in all fields correctly.')
    else:
        form = UserLoginForm()
    
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('products:home')

# ==================== EMAIL VERIFICATION ====================

def verify_email_done(request):
    """
    Page shown after registration asking user to verify email
    """
    return render(request, 'accounts/verify_email_done.html')

def verify_email_confirm(request, uidb64, token):
    """
    Handle email verification link
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user is not None and account_activation_token.check_token(user, token):
        # Mark email as verified
        profile = user.profile
        profile.email_verified = True
        profile.save()
        
        messages.success(request, 'Email verified successfully!')
        return redirect('accounts:verify_email_complete')
    else:
        messages.error(request, 'Invalid or expired verification link.')
        return redirect('accounts:verify_email_done')

def verify_email_complete(request):
    """
    Page shown after successful email verification
    """
    return render(request, 'accounts/verify_email_complete.html')

def resend_verification_email(request):
    """
    Resend verification email
    """
    if request.user.is_authenticated and not request.user.profile.email_verified:
        send_verification_email(request, request.user)
        messages.success(request, 'Verification email sent!')
    return redirect('accounts:verify_email_done')

# ==================== PROFILE MANAGEMENT ====================

@login_required
def profile_view(request):
    """
    View user profile
    """
    # Get wishlist items
    wishlist = Wishlist.objects.filter(user=request.user).select_related('product')[:5]
    
    # Get recent login history
    login_history = LoginHistory.objects.filter(user=request.user)[:10]
    
    context = {
        'user': request.user,
        'profile': request.user.profile,
        'wishlist': wishlist,
        'login_history': login_history,
    }
    return render(request, 'accounts/profile.html', context)

@login_required
@login_required
def profile_edit_view(request):
    """Edit user profile"""
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user.profile, user=request.user)
    
    context = {
        'form': form,
        'profile': request.user.profile,  # ✅ This is the key fix
    }
    return render(request, 'accounts/profile_edit.html', context)
@login_required
def password_change_view(request):
    """
    Change user password
    """
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            messages.success(request, 'Password changed successfully!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'accounts/password_change.html', {'form': form})

# ==================== PASSWORD RESET ====================

# ==================== OTP-BASED PASSWORD RESET ====================

def password_reset_otp_request(request):
    """
    Request password reset via OTP - Step 1: Enter email
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            email = email.strip()
            user = User.objects.filter(email=email, is_active=True).order_by('-date_joined').first()
            if user:
                # Create OTP and send to email
                create_password_reset_otp(user)
                # Store user ID in session for verification
                request.session['password_reset_user_id'] = user.id
                request.session['password_reset_email'] = email
                messages.success(request, 'OTP code sent to your email! Please check your inbox.')
                return redirect('accounts:password_reset_otp_verify')
            else:
                messages.error(request, 'No active account found with this email address.')
        else:
            messages.error(request, 'Please enter your email address.')
    
    return render(request, 'accounts/password_reset_otp_request.html', {'step': 1})


@csrf_exempt
@require_POST
def password_reset_otp_send_api(request):
    """
    API endpoint to send password reset OTP to an email address.
    Accepts JSON or form-data with `email`.
    """
    payload = {}
    if request.content_type == 'application/json':
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON payload.'}, status=400)
    else:
        payload = request.POST

    email = payload.get('email')
    if not email:
        return JsonResponse({'success': False, 'message': 'Email is required.'}, status=400)

    user = User.objects.filter(email=email, is_active=True).order_by('-date_joined').first()
    if user:
        create_password_reset_otp(user)
        request.session['password_reset_user_id'] = user.id
        request.session['password_reset_email'] = email
        return JsonResponse({'success': True, 'message': 'OTP code sent to your email.'})
    return JsonResponse({'success': True, 'message': 'If this email exists, an OTP code was sent.'})


def password_reset_otp_verify(request):
    """
    Verify OTP code - Step 2: Enter OTP code
    """
    user_id = request.session.get('password_reset_user_id')
    email = request.session.get('password_reset_email', '')
    
    if not user_id:
        messages.error(request, 'Please enter your email first.')
        return redirect('accounts:password_reset_otp_request')
    
    # Check if we can resend (based on last OTP sent time)
    can_resend = True
    countdown = 0
    
    if user_id:
        last_code = PasswordResetCode.objects.filter(
            user_id=user_id,
            is_used=False
        ).order_by('-created_at').first()
        
        if last_code:
            time_diff = timezone.now() - last_code.created_at
            if time_diff.total_seconds() < 600:  # 10 minutes
                can_resend = False
                countdown = 600 - int(time_diff.total_seconds())
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        
        if otp_code:
            try:
                reset_code = PasswordResetCode.objects.filter(
                    user_id=user_id,
                    code=otp_code,
                    is_used=False
                ).first()
                
                if reset_code and reset_code.is_valid():
                    # Mark code as used
                    reset_code.is_used = True
                    reset_code.save()
                    
                    # Store verification in session
                    request.session['password_reset_verified'] = True
                    messages.success(request, 'OTP verified! Please enter your new password.')
                    return redirect('accounts:password_reset_otp_set')
                else:
                    messages.error(request, 'Invalid or expired OTP code. Please try again.')
            except Exception as e:
                messages.error(request, 'An error occurred. Please try again.')
        else:
            messages.error(request, 'Please enter the OTP code.')
    
    return render(request, 'accounts/password_reset_otp_verify.html', {
        'step': 2,
        'email': email,
        'can_resend': can_resend,
        'countdown': countdown
    })


def password_reset_otp_set(request):
    """
    Set new password - Step 3: Enter new password
    """
    if not request.session.get('password_reset_verified'):
        messages.error(request, 'Please verify your identity first.')
        return redirect('accounts:password_reset_otp_request')
    
    user_id = request.session.get('password_reset_user_id')
    
    if request.method == 'POST':
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if new_password1 and new_password2:
            if new_password1 == new_password2:
                if len(new_password1) >= 8:
                    try:
                        user = User.objects.get(id=user_id)
                        user.set_password(new_password1)
                        user.save()
                        
                        # Clear session
                        del request.session['password_reset_user_id']
                        del request.session['password_reset_verified']
                        
                        messages.success(request, 'Password reset successfully! You can now login with your new password.')
                        return redirect('accounts:login')
                    except User.DoesNotExist:
                        messages.error(request, 'User not found. Please try again.')
                else:
                    messages.error(request, 'Password must be at least 8 characters.')
            else:
                messages.error(request, 'Passwords do not match.')
        else:
            messages.error(request, 'Please fill in all password fields.')
    
    return render(request, 'accounts/password_reset_otp_set.html')


def password_reset_otp_resend(request):
    """
    Resend OTP code
    """
    user_id = request.session.get('password_reset_user_id')
    
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            create_password_reset_otp(user)
            messages.success(request, 'New OTP code sent to your email!')
        except User.DoesNotExist:
            messages.error(request, 'User not found.')
    else:
        messages.error(request, 'Please enter your email first.')
    
    return redirect('accounts:password_reset_otp_verify')


# ==================== WISHLIST ====================

@login_required
def wishlist_view(request):
    """
    View user's wishlist
    """
    wishlist = Wishlist.objects.filter(user=request.user).select_related('product')
    
    # Pagination
    paginator = Paginator(wishlist, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/wishlist.html', {'page_obj': page_obj})

@login_required
def wishlist_add(request, product_id):
    """
    Add product to wishlist
    """
    from products.models import Product
    
    product = get_object_or_404(Product, id=product_id)
    
    try:
        wishlist_item, created = Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        if created:
            messages.success(request, f'{product.name} added to wishlist!')
        else:
            messages.info(request, f'{product.name} is already in your wishlist.')
    except IntegrityError:
        messages.error(request, 'An error occurred. Please try again.')
    
    return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))

@login_required
def wishlist_remove(request, product_id):
    """
    Remove product from wishlist
    """
    wishlist_item = get_object_or_404(
        Wishlist, 
        user=request.user, 
        product_id=product_id
    )
    product_name = wishlist_item.product.name
    wishlist_item.delete()
    
    messages.success(request, f'{product_name} removed from wishlist.')
    return redirect('accounts:wishlist')

# ==================== ACCOUNT SETTINGS ====================

@login_required
def account_settings(request):
    """
    Account settings page
    """
    return render(request, 'accounts/settings.html')

@login_required
def delete_account(request):
    """Delete user account permanently"""
    
    if request.method == 'POST':
        # Get the confirmation text from the form
        confirm_text = request.POST.get('confirm_text', '')
        password = request.POST.get('password', '')
        
        # Verify the user typed DELETE
        if confirm_text != 'DELETE':
            messages.error(request, 'Please type DELETE to confirm account deletion.')
            return redirect('accounts:delete_account')
        
        # Verify password
        from django.contrib.auth import authenticate
        user = authenticate(username=request.user.username, password=password)
        
        if not user:
            messages.error(request, 'Incorrect password. Please try again.')
            return redirect('accounts:delete_account')
        
        try:
            with transaction.atomic():
                # Store user info for email (before deletion)
                user_email = request.user.email
                user_username = request.user.username
                
                # Logout the user before deletion
                logout(request)
                
                # Delete the user (cascade will delete profile, wishlist, etc.)
                user.delete()
                
                # Send confirmation email (optional)
                try:
                    send_mail(
                        subject='Account Deleted - MyEcom',
                        message=f'Dear {user_username},\n\nYour account has been successfully deleted from MyEcom.\n\nAll your personal data has been removed from our system.\n\nIf you did not request this, please contact our support team immediately.\n\nBest regards,\nMyEcom Team',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user_email],
                        fail_silently=True,
                    )
                except:
                    pass  # Email sending failed, but account deletion succeeded
                
                messages.success(request, 'Your account has been permanently deleted. We\'re sorry to see you go!')
                return redirect('products:home')
                
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
            return redirect('accounts:delete_account')
    
    return render(request, 'accounts/delete_account.html')
# ==================== LOGIN HISTORY ====================

@login_required
def login_history_view(request):
    """
    View user's login history
    """
    history = LoginHistory.objects.filter(user=request.user)
    
    # Pagination
    paginator = Paginator(history, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'accounts/login_history.html', {'page_obj': page_obj})
