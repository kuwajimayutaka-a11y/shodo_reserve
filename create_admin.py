import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shodo_reserve.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

email = os.environ.get("DJANGO_ADMIN_EMAIL")
name = os.environ.get("DJANGO_ADMIN_USER", "管理者")
password = os.environ.get("DJANGO_ADMIN_PASSWORD")

if not email or not password:
    print("DJANGO_ADMIN_EMAIL and DJANGO_ADMIN_PASSWORD are required. Skipping.")
elif not User.objects.filter(email=email).exists():
    User.objects.create_superuser(email=email, name=name, password=password)
    print(f"Created superuser: {email}")
else:
    print(f"Superuser {email} already exists. Skipping.")
