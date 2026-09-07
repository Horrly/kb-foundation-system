import random
from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone
from donors.models import Donation, Donor
from expenditures.models import Expenditure
from accounts.models import CustomUser


class Command(BaseCommand):
    help = "Calculates the total balance and creates a massive donation if the balance is too low."

    def handle(self, *args, **options):
        # Calculate Total Expenditures
        total_exp = Expenditure.objects.aggregate(total=Sum('amount'))['total'] or 0
        
        # Calculate Total Confirmed Donations
        total_don = Donation.objects.filter(
            status=Donation.Status.CONFIRMED
        ).aggregate(total=Sum('amount_confirmed'))['total'] or 0

        balance = total_don - total_exp
        target_surplus = 5000000

        self.stdout.write(f"Current Total Donations: NGN {total_don:,.2f}")
        self.stdout.write(f"Current Total Expenditures: NGN {total_exp:,.2f}")
        self.stdout.write(f"Current Balance: NGN {balance:,.2f}")

        if balance < target_surplus:
            deficit = target_surplus - balance
            # Add a 15,000,000 buffer on top of the deficit to guarantee a massive surplus
            injection_amount = deficit + 15000000
            
            self.stdout.write(self.style.WARNING(f"[INFO] Balance is low. Injecting NGN {injection_amount:,.2f} to fix data sanity..."))
            
            # Get or create an anonymous donor
            anon_user, created = CustomUser.objects.get_or_create(
                username="anon_philanthropist@demo.com",
                defaults={
                    'email': 'anon_philanthropist@demo.com',
                    'role': CustomUser.Role.DONOR,
                    'first_name': 'Anonymous',
                    'last_name': 'Philanthropist',
                }
            )
            
            if created:
                anon_user.set_password('DemoPassword123!')
                anon_user.save()
                
            donor, _ = Donor.objects.get_or_create(
                user=anon_user,
                defaults={
                    'full_name': 'Anonymous Philanthropist',
                    'email': 'anon_philanthropist@demo.com',
                    'phone': '08000000000',
                    'address': 'Global'
                }
            )
            
            # Create the massive donation
            Donation.objects.create(
                donor=donor,
                amount=injection_amount,
                amount_confirmed=injection_amount,
                date=timezone.now().date(),
                payment_method=Donation.PaymentMethod.BANK_TRANSFER,
                reference_number=f"DEMO-FIX-{random.randint(1000, 9999)}",
                status=Donation.Status.CONFIRMED,
                admin_notes="Auto-injected by fix_balance for demo data sanity.",
                reviewed_at=timezone.now()
            )
            
            new_balance = balance + injection_amount
            self.stdout.write(self.style.SUCCESS(f"[OK] Injected NGN {injection_amount:,.2f}. New balance is NGN {new_balance:,.2f}!"))
        else:
            self.stdout.write(self.style.SUCCESS(f"[OK] Balance is already healthy (NGN {balance:,.2f}). No action needed."))
