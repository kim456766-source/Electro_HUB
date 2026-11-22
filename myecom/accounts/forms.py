from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, PasswordChangeForm
from django.contrib.auth import password_validation
from django.contrib.auth import get_user_model
from .models import Profile, User, SellerProfile

# Get the custom user model
User = get_user_model()

# ========== REGISTRATION FORMS ==========

class CustomerRegistrationForm(UserCreationForm):
    """Form for customer registration"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'})
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'customer'
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user

class SellerRegistrationForm(UserCreationForm):
    """Form for seller registration"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email'})
    )
    first_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'})
    )
    store_name = forms.CharField(
        max_length=200, 
        required=True, 
        label='Store Name',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter store name'})
    )
    store_description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe your store'}),
        required=True, 
        label='Store Description'
    )
    phone = forms.CharField(
        max_length=20, 
        required=True, 
        label='Phone Number',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter phone number'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Enter address'}),
        required=False, 
        label='Address'
    )
    city = forms.CharField(
        max_length=100, 
        required=False, 
        label='City',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter city'})
    )
    payment_method = forms.ChoiceField(
        choices=[
            ('mtn_money', 'MTN Money'),
            ('bank_transfer', 'Bank Transfer'),
            ('paypal', 'PayPal'),
        ],
        required=True,
        label='Payment Method',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    payment_account = forms.CharField(
        max_length=200, 
        required=True, 
        label='Payment Account',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter payment account details'})
    )
    store_logo = forms.ImageField(
        required=False, 
        label='Store Logo',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2',
                  'store_name', 'store_description', 'phone', 'address', 'city', 
                  'payment_method', 'payment_account', 'store_logo']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Enter password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'seller'
        user.is_approved = True  # Auto-approve
        user.business_name = self.cleaned_data['store_name']
        user.business_description = self.cleaned_data['store_description']
        user.phone_number = self.cleaned_data['phone']
        user.address = self.cleaned_data['address']
        
        # Handle store logo
        if 'store_logo' in self.files:
            user.business_logo = self.files['store_logo']
        
        if commit:
            user.save()
            # Create seller profile with payment info
            SellerProfile.objects.get_or_create(
                user=user,
                defaults={
                    'payment_method': self.cleaned_data['payment_method'],
                    'payment_account': self.cleaned_data['payment_account'],
                    'city': self.cleaned_data['city'],
                    'commission_rate': 10.00
                }
            )
        return user

# Alias for backward compatibility
UserRegistrationForm = CustomerRegistrationForm

# ========== LOGIN FORM ==========

class UserLoginForm(forms.Form):
    """Form for user login"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username or email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

# ========== PROFILE FORMS ==========

class UserProfileForm(forms.ModelForm):
    """Form for editing user profile"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Profile
        fields = ['phone', 'address', 'city', 'postal_code', 'country', 
                 'profile_picture', 'newsletter_subscribed']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.Select(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'newsletter_subscribed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Initialize with user data
        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email
    
    def save(self, commit=True):
        # Save user data
        if self.user:
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            if commit:
                self.user.save()
        
        # Save profile data
        return super().save(commit)

# Alias for backward compatibility
UserUpdateForm = UserProfileForm
ProfileUpdateForm = UserProfileForm

# ========== PASSWORD FORMS ==========

class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with Bootstrap styling"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = f'Enter {field.label.lower()}'

class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError('No user found with this email address.')
        return email

class SetPasswordForm(forms.Form):
    """Form for setting new password"""
    new_password1 = forms.CharField(
        label='New password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text=password_validation.password_validators_help_text_html()
    )
    new_password2 = forms.CharField(
        label='Confirm new password',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        
        # Validate password strength
        if password1:
            password_validation.validate_password(password1)
        
        return cleaned_data