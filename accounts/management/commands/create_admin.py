from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Automatically creates a default admin user on Render if it does not exist'

    def handle(self, *args, **options):
        User = get_user_model()
        username = 'admin'
        email = 'admin@kbfoundation.com'
        password = 'AdminPassword123!'  # You can change this to your preferred password

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully!'))
        else:
            self.stdout.write(self.style.WARNING('Superuser already exists.'))