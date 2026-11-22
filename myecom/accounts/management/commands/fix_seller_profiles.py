from django.core.management.base import BaseCommand
from accounts.models import User, SellerProfile

class Command(BaseCommand):
    help = 'Create missing seller profiles for existing seller users'
    
    def handle(self, *args, **kwargs):
        # Get all users with role 'seller' who don't have a profile
        sellers_without_profile = User.objects.filter(
            role='seller'
        ).exclude(
            id__in=SellerProfile.objects.values_list('user_id', flat=True)
        )
        
        count = 0
        for seller in sellers_without_profile:
            SellerProfile.objects.create(user=seller)
            count += 1
            self.stdout.write(f"✓ Created profile for: {seller.username}")
        
        if count > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Successfully created {count} seller profiles")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("✅ All sellers already have profiles!")
            )
        
        # Show statistics
        total_sellers = User.objects.filter(role='seller').count()
        profiles_count = SellerProfile.objects.count()
        self.stdout.write(f"\n📊 Statistics:")
        self.stdout.write(f"   Total sellers: {total_sellers}")
        self.stdout.write(f"   Total profiles: {profiles_count}")