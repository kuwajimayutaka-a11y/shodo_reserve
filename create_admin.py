# create_admin.py
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shodo_reserve.settings")
django.setup()

User = get_user_model()

username = os.environ.get("DJANGO_ADMIN_USER")
email = os.environ.get("DJANGO_ADMIN_EMAIL", "")
password = os.environ.get("DJANGO_ADMIN_PASSWORD")

if not username or not password:
    print("DJANGO_ADMIN_USER and DJANGO_ADMIN_PASSWORD are required. Skipping.")
elif not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Created superuser: {username}")
else:
    print(f"Superuser {username} already exists. Skipping.")
