from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, SellerProfile, Profile

@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    """Create profiles when a new user is created"""
    if created:
        # Create Profile for all users
        Profile.objects.get_or_create(user=instance)
        
        # Create SellerProfile only for sellers and only if it doesn't exist
        if instance.role == 'seller':
            SellerProfile.objects.get_or_create(
                user=instance,
                defaults={
                    'payment_method': None,
                    'payment_account': None,
                    'city': instance.city if hasattr(instance, 'city') else None,
                    'commission_rate': 10.00
                }
            )
            print(f"✅ Seller profile created for: {instance.username}")

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