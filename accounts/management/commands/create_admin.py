from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Automatically creates a default admin user on Render with admin role'

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'admin'
        email = 'admin@kbfoundation.com'
        password = 'AdminPassword123!'

        user, created = User.objects.get_or_create(username=username, defaults={'email': email, 'role': 'admin'})
        if created:
            user.set_password(password)
            user.is_superuser = True
            user.is_staff = True
            user.role = 'admin'
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created with admin role!'))
        else:
            # Ensure existing admin has the correct role
            user.role = 'admin'
            user.is_superuser = True
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.WARNING('Superuser already exists, updated role to admin.'))