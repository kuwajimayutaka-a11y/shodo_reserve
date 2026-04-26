# create_admin.py
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "shodo_reserve.settings")
django.setup()

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
    user = User.objects.get(email=email)
    user.set_password(password)
    user.name = name
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"Updated superuser: {email}")
